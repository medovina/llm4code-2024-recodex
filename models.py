from dataclasses import dataclass
import json
import pprint
import time
from typing import cast

import google.api_core.exceptions
import openai
from openai.error import APIError, InvalidRequestError, RateLimitError, ServiceUnavailableError
from openai.error import Timeout
from openai.openai_object import OpenAIObject
import replicate
import replicate.exceptions
import tiktoken
from vertexai.preview.language_models import CodeGenerationModel

from util import *

models = [('code-bison-32k', 'code-bison', 32 * 1024),
          ('codellama-34b', 'codellama', 100_000),
          ('gpt-3.5-turbo-1106', 'gpt-3.5', 16 * 1024),
          ('gpt-4-1106-preview', 'gpt-4', 128 * 1024)]

def find_model(name):
    matches = [ms for ms in models if name in ms[0]]
    if len(matches) == 0:
        print('unknown model')
        exit()
    if len(matches) > 1:
        print('ambiguous model name')
        exit()
    return matches[0]

def get_engine(model):
    if model.startswith('code-bison'):
        return Codey(model)
    elif model.startswith('codellama'):
        return Llama(model)
    elif model.startswith('gpt-'):
        return GPT(model)
    else:
        assert False, 'no engine'

@dataclass
class ModelResult:
    program: str = ''
    error: str = ''

class TextModel:
    def token_count(self, s):
        return len(s) // 3

    def sys_message(self, content):
        return content
    
    def user_message(self, content):
        return '\n[EXERCISE]\n\n' + content
    
    def assistant_message(self, content):
        return '\n[RESPONSE]\n\n' + content

    def make_prompt(self, messages, verbose):
        prompt = ''.join(messages + [self.assistant_message('')])
        if verbose:
            print(prompt, end = '')
        return prompt

class Codey(TextModel):
    def __init__(self, model):
        self.model = CodeGenerationModel.from_pretrained(model)

    def query(self, seed, messages, func, verbose):
        prompt = self.make_prompt(messages, verbose)
        try:
            response = self.model.predict(prompt, max_output_tokens = 5000).text
            return ModelResult(response, '')
        except google.api_core.exceptions.InvalidArgument as e:
            if 'Text is too long' in e.message:
                return ModelResult('', 'text is too long')
            raise e

llama_versions = {
    'codellama-34b' : 'efbd2ef6feefb242f359030fa6fe08ce32bfced18f3868b2915db41d41251b46',
}

class Llama(TextModel):
    def __init__(self, model):
        self.model = model
        self.version = llama_versions[model]

    def query(self, seed, messages, func, verbose):
        sys_prompt = messages[0]
        if verbose:
            print(sys_prompt)
        prompt = self.make_prompt(messages[1:], verbose)

        try:
            output = replicate.run(
                f'meta/{self.model}:{self.version}',
                input = { 'system_prompt': sys_prompt, 'prompt': prompt, 'max_tokens' : 5000 }
            )
            s = ''
            stop = '[EXERCISE]'
            for c in output:
                s += c
                if stop in s[-20:]:
                    i = s.index(stop)
                    s = s[:i]
                    break
        except replicate.exceptions.ModelError as e:
            message = e.args[0]
            if 'exceed context window' in message:
                return ModelResult('', 'context window exceeded')
            raise e
                
        return ModelResult(s, '')

openai.api_key_path = '../openai_api_key'

pp = pprint.PrettyPrinter(width = 120)

@dataclass
class GptResult(ModelResult):
    fingerprint: str = ''
    
    in_tokens: int = 0
    out_tokens: int = 0
    total_tokens: int = 0

    funcall: str | None = None
    input: str | None = None
    expr: str | None = None

def message(role, content):
    return { 'role' : role, 'content' : content }

class GPT:
    def __init__(self, model):
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)

    def token_count(self, s):
        return len(self.encoding.encode(s))

    def sys_message(self, content):
        return message('system', content)
    
    def user_message(self, content):
        return message('user', content)

    def assistant_message(self, content):
        return message('assistant', content)

    def fun_call(self, fun, args):
        return { 'role' : 'assistant', 'content' : '',
                 'function_call' : { 'name' : fun, 'arguments' : json.dumps(args) } }

    def fun_result(self, function_name, output):
        return { 'role': 'function', 'name': function_name, 'content': json.dumps(output) }

    def show_messages(self, messages):
        for m in messages:
            role = m['role']
            print(f"\n[{role}]")
            if f := m.get('function_call'):
                name = f['name']
                print(f'  call function {name}(program, input)')
                args = json.loads(f['arguments'])
                print('    program:')
                print(indent_by(6, args['program']))
                for arg_name in ['input', 'expression']:
                    if s := args.get(arg_name):
                        print(f'    {arg_name}:')
                        print(indent_by(6, s))
            elif role == 'function':
                name = m['name']
                print(f'  returned from function {name}():')
                print(indent_by(4, json.loads(m['content'])))
            else:
                print(m['content'], end = '')

    def query_gpt(self, seed, messages, funs):
        delay = 1.0
        while True:
            try:
                args = { 'model' : self.model, 'messages' : messages, 'seed' : seed }
                if funs:
                    args['functions'] = funs
                response = openai.ChatCompletion.create(**args)
                break
            except APIError:
                print('API error, retrying...')
            except RateLimitError:
                print('rate limit exceeded, retrying...')
            except ServiceUnavailableError:
                print('service unavailable, retrying...')
            except Timeout:
                print('timeout error, retrying...')
            time.sleep(delay)
            delay *= 1.5
            
        return cast(OpenAIObject, response)

    def query(self, seed, messages, funs, verbose):
        gres = GptResult()

        if verbose:
            self.show_messages(messages)
            if funs:
                pp.pprint(funs)

        try:
            response = self.query_gpt(seed, messages, funs)
        except InvalidRequestError as e:
            if 'Detected an error in the prompt' in cast(str, e.user_message):
                gres.error = 'prompt error'
                return gres
            raise e

        if verbose:
            pp.pprint(response)

        gres.fingerprint = response['system_fingerprint']
        usage = response['usage']
        gres.in_tokens = int(usage['prompt_tokens'])
        gres.out_tokens = int(usage['completion_tokens'])
        gres.total_tokens = int(usage['total_tokens'])
        
        response_message = response['choices'][0]['message']
        messages.append(response_message)
        
        if response_message.get('function_call'):
            call = response_message['function_call']
            gres.funcall = call['name'].lower()

            try:
                args = json.loads(call['arguments'])
            except json.decoder.JSONDecodeError:
                print("can't decode arguments:\n" + call['arguments'])
                gres.error = 'invalid arguments'
                return gres

            gres.program = args['program'].strip()

            gres.input = args.get('input')
            gres.expr = args.get('expression')
        else:
            gres.program = response_message['content']

        return gres

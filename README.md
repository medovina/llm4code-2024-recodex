# Tackling Students' Coding Assignments with LLMs

This repository contains code and data used in producing the paper "Tackling Students' Coding Assignments with LLMs" by Adam Dingle and Martin Kruliš.  It is organized as follows:

* Top-level directory: Python code used for running evaluations.
* examples/ :  Example programs for few-shot prompting as described in section 3.4 of the paper.
* exercises/ : Metadata about exercises (exercises.csv) and courses (courses.csv), plus Python code for manipulating exercises.
* lang/ : Minor language-specific helper files.
* plots/ : Plots for the paper, generated from results files.
* results/ : CSV files with evaluation results.
* stats/ : CSV files with statistics, generated from results files.

Some data is intentionally omitted from this repository, namely

* the subdirectories of exercises/ that contain the actual text of exercises
* the directory solutions/ that contains the solutions generated by the models

We cannot make the exercises public, because they have many authors who would need to give permission for that, and also because we do not want them or their solutions to be available to students.  We are willing to provide them privately for review or research purposes [under certain conditions](tree/main/exercises).

### Exercise metadata

The file exercise/exercises.csv contains metadata about our set of exercises.  The fields in this file include

* id - A unique ID for the exercise.
* name - The exercise name in either Czech or English.
* text_length - Length of the exercise description in bytes.
* locale - "cs" if the exercise is in Czech, otherwise "en".
* created_at - A timestamp indicating when the exercise was written.
* assignments_count - The number of times that this exercise has ever been assigned to a group of students.
* solvers_count - The number of students who have ever solved the exercise.
* solutions_count - The number of solutions ever submitted by students.
* attachments_count - The number of attachments in the exercise.
* runtime - The programming language in which we will ask models to solve the exercise in our evaluation.
* course - The course to which this exercise belongs.  We use this field to assign exercises to courses manually if they can't be automatically assigned from group_name_1 and group_name_2.
* ref_best_score - The best score of any reference solution for the exercise.  If this is not 1, we will exclude the exercise from our evaluation.
* tests_count - number of test cases (for the solution evaluation)
* avg_score, ... - More fields with statistics about the exercise's solutions on ReCodEx, not documented in detail at this time.

More details can be found in [exercises/README.md](tree/main/exercises).

### Results files

The CSV files in the results/ directory contain the results of solution evaluations.  For the GPT-3.5 and GPT-4 models there are 5 results files, containing the evaluations of our 5 independent queries to these models.

The columns in the results CSV file have the following meanings:

* time - The time at which we generated and evaluated this solution.
* fprint - For GPT models, the fingerprint returned by the OpenAI API.
* seed - For GPT models, a seed that we sent in the OpenAI query.
* id - The ReCodEx ID of an exercise.
* group1, group2 - The exercise's group IDs, copied from group_name_1 and group_name_2 in exercises.csv.
* name - The exercise's name in the language in which it was submitted.
* runtime - The runtime (programming language) in which we evaluated the exercise.
* lang - The lang of the exercise, either "en" for English or "cs" for Czech.
* num_atts - The number of attachments that the exercise has in ReCodEx.  Note that each file inside a .zip counts as a separate attachment.  (The .zip file itself does not count as an attachment.)
* sub_atts - The number of attachments that eval.py actually submitted for the exercise, which might be less than num_atts if some attachments were not submittable (e.g. image files) or were too large.
* in_tokens - The count of tokens in the text that was sent to the model, including the prompt, the exercise specification and all attachments.
* out_tokens - The count of tokens in the text that the model returned.
* total_tokens - The sum of in_tokens and out_tokens.
* score - ReCodEx's evaluation score for the solution.  This is the fraction of test cases that passed (note that test cases may have various weights in computing this fraction).
* tests - The number of test cases in ReCodEx for this exercise.  (If the exercise was not evaluated because the model didn't produce a valid program, this will be 1.)
* passed - The number of tests that passed.
* comp_err - The number of tests that failed due to a compilation error.
* rt_err - The number of tests that failed to a runtime error, such as an array index out of bounds.
* wrong_output - The number of tests that failed because they produced incorrect output.
* time_limit - The number of tests that failed because the time limit was exceeded.
* mem_limit - The number of tests that failed because the memory limit was exceeded.
* other_err - A 1 in this column means that some other error occurred, e.g. the model did not produce a valid program or the ReCodEx evaluation failed unexpectedly.
* error_msg - A message giving more details about an other_err.


### Repeating our experiments

If you wish to repeat our experiments, you will need several things:

* The actual text of the exercises, which we can provide upon request.
* An account at OpenAI for querying GPT-3.5 and GPT-4.
* An account in Google Cloud for querying Codey.
* An account at replicate.com for querying Code Llama.  (Alternately you could modify the code here so that it queries Code Llama somewhere else.)
* Access to the ReCodEx system for evaluating solutions.  You could attempt to run your own instance of ReCodEx, though setting it up will be complicated.  If you want to access our instance, contact the authors and we can discuss it.

To regenerate our results, delete the "results" and "solutions" directories, then run

```
$ python eval.py bison
$ python eval.py llama
$ python eval.py gpt-3 -s 1
$ python eval.py gpt-3 -s 2
$ python eval.py gpt-3 -s 3
$ python eval.py gpt-3 -s 4
$ python eval.py gpt-3 -s 5
$ python eval.py gpt-4 -s 1
$ python eval.py gpt-4 -s 2
$ python eval.py gpt-4 -s 3
$ python eval.py gpt-4 -s 4
$ python eval.py gpt-4 -s 5
```

For every exercise, this will generate and evaluate 1 solution for Codey and Code Llama, and 5 solutions for GPT-3.5 and GPT-4.  These queries will take several days to complete and will use about $100 of OpenAI API credit at current prices.

All solutions from models will be stored in the "solutions" directory, and their evaluations will be stored in the "results" directory.  After that, you can generate the plots in the paper by running

```
$ python plot.py
```

You can generate statistics CSV files in the "stats" directory by running

```
$ python stats.py bison
$ python stats.py llama
$ python stats.py gpt-3
$ python stats.py gpt-4
```

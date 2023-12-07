import java.util.Scanner;

class Sum {
    public static void main(String[] args) {
        Scanner s = new Scanner(System.in);
        int i = Integer.valueOf(s.nextLine());
        int j = Integer.valueOf(s.nextLine());
        s.close();
        
        System.out.println(i + j);
    }
}

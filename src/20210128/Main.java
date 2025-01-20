
import java.io.File;
import java.io.FileNotFoundException;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;

public class Main {

    public static void processFile(String filename) {
        List<Integer> numbers = new ArrayList<>();

        try (Scanner sc = new Scanner(new File(filename))) {
            while (sc.hasNextInt()) {
                numbers.add(sc.nextInt());
            }
        } catch (FileNotFoundException e) {
            System.err.println(e.getMessage());
            return;
        }

        for (Integer n : numbers) {
            for (Integer m : numbers) {
                if (n + m == 2021) {
                    System.out.println(n + " " + m);
                    return;
                }
            }
        }
        System.out.println("No pair found with a sum of 2021");
    }

    public static void main(String[] args) {
        processFile("src/main.txt");
    }

}


public class Guesser {

    public static int solve(Challenger challenger, int lowest, int highest) {

        int guess = (lowest + highest) / 2;
        int result = challenger.guess(guess);
        return switch (result) {
            case 0 ->
                guess;
            case 1 ->
                solve(challenger, lowest, guess - 1);
            default ->
                solve(challenger, guess + 1, highest);
        };
    }

    public static void main(String[] args) {
        Challenger challenger = new Challenger();
        int result = solve(challenger, 0, 99);
        System.out.println(result);
    }
}

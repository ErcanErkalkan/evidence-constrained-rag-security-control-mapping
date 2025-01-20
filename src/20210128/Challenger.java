
import java.util.Random;

public class Challenger {

    private final int number;

    public Challenger() {
        this.number = new Random().nextInt(100);
    }

    public int guess(int number) {
        if (this.number == number) {
            return 0;
        } else if (this.number < number) {
            return 1;
        } else {
            return -1;
        }
    }
}

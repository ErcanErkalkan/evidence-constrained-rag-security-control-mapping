import java.util.HashMap;
import java.util.Map;

public class Inventory {

  private Map<Topping, Integer> amounts = new HashMap<>();

  public Inventory() {
    for (Topping topping : Topping.values()) {
      amounts.put(topping, 10);
    }
  }

  // @requires topping != null;
  // @requires amount >= 0
  // @ensures amaunts.get(topping) == \old(amaunts.get(topping))+amount
  // @ensures (\forall Topping t; t != topping ==> amaunts.get(t) ==
  // \old(amaunts.get(topping)));
  public synchronized void refill(Topping topping, int amount) {
    amounts.put(topping, amounts.get(topping) + amount);
    notifyAll();
  }
  /*
   * public void refill(Topping topping, int amount) {
   * amounts.put(topping, amounts.get(topping) + amount);
   * }
   */

  /*
   * public boolean take(Topping topping) {
   * int current = amounts.get(topping);
   * if (current > 0) {
   * amounts.put(topping, current - 1);
   * return true;
   * } else {
   * return false;
   * }
   * }
   */

  /*
   * public boolean take(Topping topping) throws NoToppingsLeftException {
   * int current = amounts.get(topping);
   * if (current > 0) {
   * amounts.put(topping, current - 1);
   * return true;
   * } else {
   * // return false;
   * throw new NoToppingsLeftException();
   * }
   * }
   */

  /*
   * public synchronized boolean take(Topping topping) throws
   * NoToppingsLeftException {
   * 
   * int current = amounts.get(topping);
   * if (current > 0) {
   * amounts.put(topping, current - 1);
   * return true;
   * } else {
   * // return false;
   * throw new NoToppingsLeftException();
   * }
   * }
   */

  public synchronized void take(Topping topping) {

    try {
      while (amounts.get(topping) <= 0) {
        wait();
      }
      amounts.put(topping, amounts.get(topping) - 1);

    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
    }

  }
}

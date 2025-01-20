import java.util.List;

public class PizzaOptimizer {
  public static void main(String[] args) {
    ToppingRules rules = new ToppingRules();
    rules.addRule(new TwoToppingsRule(Topping.ONIONS, Topping.SALAMI, 1.25)); // contains both onions and salami:
                                                                              // multiply value by 1:25
    rules.addRule(new OneToppingRule(Topping.MUSHROOMS, 1.2)); // contains mushrooms: multiply value by 1:2
    rules.addRule(new OneToppingRule(Topping.PINEAPPLE, 0.2));// contains pineapple: multiply value by 0:2

    double bestValue = 0;
    List<Topping> bestComnination = null;

    for (Topping t1 : Topping.values()) {
      for (Topping t2 : Topping.values()) {
        for (Topping t3 : Topping.values()) {
          List<Topping> combination = List.of(t1, t2, t3);
          double value = rules.evaluate(combination);
          if (value >= bestValue) {
            bestValue = value;
            bestComnination = combination;
          }
        }
      }
    }
    System.out.println("Best combination: " + bestComnination);
    System.out.println("Best value: " + bestValue);
  }
}

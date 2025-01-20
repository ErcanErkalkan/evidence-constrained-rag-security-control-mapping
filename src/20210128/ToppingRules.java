import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public class ToppingRules {

  private final List<ToppingRule> rules = new ArrayList<>();

  public void addRule(ToppingRule rule) {
    rules.add(rule);
  }

  public double evaluate(Collection<Topping> toppings) {
    double value = 10.0;
    for (ToppingRule rule : rules) {
      value = rule.apply(toppings, value);
    }
    return value;
  }
}

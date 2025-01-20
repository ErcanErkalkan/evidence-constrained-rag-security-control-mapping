import java.util.Collection;

public class OneToppingRule implements ToppingRule {

  private final Topping topping;
  private final double modifier;

  public OneToppingRule(Topping topping, double modifier) {
    this.topping = topping;
    this.modifier = modifier;
  }

  @Override
  public double apply(Collection<Topping> toppings, double value) {
    if (toppings.contains(topping)) {
      value = value * modifier;
    }
    return value;
  }
}

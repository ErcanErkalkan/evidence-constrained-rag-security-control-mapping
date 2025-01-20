
/**
 * An item in the E-Shop Inc. shop. There can be multiple items with the same ID
 * in the shop, as long as they have the same name. Items with the same ID could
 * have the same prices and descriptions or a different price or description.
 */

public interface ShopItem {

    /**
     * Return the ID of this item.
     *
     * @return the id
     */
    // @ ensures \result >= 10000 && \result <= 99999;
    // @ pure
    int getId();

    /**
     * Return the name of this item. Items with the same ID have the same name.
     *
     * @return the name
     */
    // @ ensures \result.length() > 0 && \result.length() <= 50;
    // @ pure
    String getName();

    int getValueInCents();

    String getDescription();
}

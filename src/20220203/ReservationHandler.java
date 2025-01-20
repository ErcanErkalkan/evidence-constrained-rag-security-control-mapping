
import java.util.Set;

public class ReservationHandler {

    private Store store;
    private Set<ShopItem> reservedItems;

    public ReservationHandler(Store store) {
        this.store = store;
    }

    /// ... constructors, getters, setters, etc ... ///
    /**
    * Reserve an item in the shop. Returns true when successful, or false
    * when the item is already reserved.
    */
    public synchronized boolean reserveItem(ShopItem item) throws NotInTheStoreException {
        if (!store.hasItem(item)) {
            throw new NotInTheStoreException();
        }

        if (reservedItems.contains(item)) {
            return false;
        } else {
            reservedItems.add(item);
            return true;
        }
    }

    /**
     * Remove an item from the reservation list (either it is bought or it is no
     * longer reserved)
     */
    public synchronized void releaseReservedItem(ShopItem item) {
        if (reservedItems.contains(item)) {
            reservedItems.remove(item);
            notifyAll();
        }
    }

    public static void main(String[] args) {
        ReservationHandler handler = new ReservationHandler(new Store());
        ShopItem item = new Item();

        try {
            handler.reserveItem(item);
        } catch (NotInTheStoreException e) {
            System.out.println("Error: " + e.getMessage());
        }
    }

    public boolean waitForItem(ShopItem item) {

        try {
            while (reservedItems.contains(item)) {
                wait();
            }
            if (!store.hasItem(item)) {
                return false;
            }
            reservedItems.add(item);
            return true;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }
}

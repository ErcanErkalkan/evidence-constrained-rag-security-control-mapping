
public class NotInTheStoreException extends Exception {

    public NotInTheStoreException() {
        super("Item is not in the store!");
    }

    public NotInTheStoreException(String message) {
        super(message);
    }

}

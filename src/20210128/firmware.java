
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class firmware {

    public static String hex(byte[] bytes) {
        StringBuilder result = new StringBuilder();
        for (byte aByte : bytes) {
            result.append(String.format("%02x", aByte));
        }
        return result.toString();
    }

    private static byte[] sha256(String text) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(text.getBytes(StandardCharsets.UTF_8));
            return hash;
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }
    private static final String adminPasswordSHA256
            = "e5f0d2bc06f4abc1cdcc51b99159a8285b9bf83aeb70e682bb168448d96613eb";

    public static void main(String[] args) {
        char[] chars = ("abcdefghijklmnopqrstuvwxyz" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ").toCharArray();

        for (char c : chars) {
            String s4 = String.valueOf(c).repeat(4);
            String s5 = String.valueOf(c).repeat(5);
            if (hex(sha256(s4)).equals(adminPasswordSHA256)) {
                System.out.println(s4);
            }
            if (hex(sha256(s5)).equals(adminPasswordSHA256)) {
                System.out.println(s5);
            }
        }
    }
}

import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Random;

/**
 * Java side of the shared-memory proofs (see docs/PERF_SHARED_MEMORY.md, host Fiji / QuPath).
 *
 *   mode "appose": the Appose 0.12.0 SharedMemory (JNA: shm_open + mmap on Linux/macOS, CreateFileMapping on Windows), the
 *                  class Fiji already ships; compiled with --release 8.
 *   mode "mmap"  : JDK only (Java 8+): FileChannel.map over a file in /dev/shm (RAM-backed on Linux).
 *   mode "ffm"   : Java 21 Foreign Function and Memory API (preview in 21): shm_open + mmap without JNA. Compile with
 *                  --enable-preview --release 21 and run with --enable-preview.
 *
 * Fills a short[] image (what ImageJ holds: one short[] per plane) into the block, prints one JSON line the Python side reads:
 * {"mode","name","shape":[h,w],"dtype":"uint16","max":N,"fill_s":x}. The block stays alive until the Python side writes "done" to stdin.
 */
public class ShmProof {
    static final int SIDE = Integer.getInteger("side", 4096);

    public static void main(String[] args) throws Exception {
        String mode = args[0];
        int h = SIDE, w = SIDE;
        short[] pixels = new short[h * w];
        Random r = new Random(1);
        int max = 0; long sum = 0;
        for (int i = 0; i < pixels.length; i++) {
            int v = r.nextInt(65536);               // above 255 and above 32767: exposes byte order and signedness mistakes
            pixels[i] = (short) v;
            max = Math.max(max, v); sum += v;
        }
        long nbytes = (long) pixels.length * 2;
        String name;
        long t0 = System.nanoTime();
        AutoCloseable owner;
        if (mode.equals("appose")) {
            org.apposed.appose.SharedMemory shm = org.apposed.appose.SharedMemory.create(nbytes);
            ByteBuffer buf = shm.buf(0, nbytes).order(ByteOrder.nativeOrder());
            buf.asShortBuffer().put(pixels);
            name = shm.name();
            owner = shm;
        } else if (mode.equals("mmap")) {
            name = "lc_java_proof_" + java.util.UUID.randomUUID().toString().substring(0, 8);
            Path file = Paths.get("/dev/shm", name);
            RandomAccessFile raf = new RandomAccessFile(file.toFile(), "rw");
            raf.setLength(nbytes);
            MappedByteBuffer buf = raf.getChannel().map(FileChannel.MapMode.READ_WRITE, 0, nbytes);
            buf.order(ByteOrder.nativeOrder()).asShortBuffer().put(pixels);
            owner = () -> { raf.close(); Files.deleteIfExists(file); };
        } else {
            throw new IllegalArgumentException(mode);
        }
        double fill = (System.nanoTime() - t0) / 1e9;
        System.out.println("{\"mode\":\"" + mode + "\",\"name\":\"" + name + "\",\"shape\":[" + h + "," + w
            + "],\"dtype\":\"uint16\",\"max\":" + max + ",\"sum\":" + sum + ",\"first\":" + (pixels[0] & 0xFFFF) + ",\"fill_s\":" + fill + "}");
        System.out.flush();
        System.in.read();                           // the host keeps the block until the task is over
        owner.close();
    }
}

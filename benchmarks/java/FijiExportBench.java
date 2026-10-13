import ij.ImagePlus;
import ij.io.FileSaver;
import ij.process.ShortProcessor;
import java.io.File;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.util.Random;

/**
 * What Fiji's host code pays to hand an open image to the worker, measured with the ImageJ that Fiji ships (ij 1.54p):
 *   tiff_disk  FileSaver.saveAsTiff to a file (what LabConstrictor_Tools.groovy does today)
 *   tiff_shmfs the same into /dev/shm (CPU cost of the encoder, no disk)
 *   shm_appose Appose 0.12.0 SharedMemory + ShortBuffer.put(short[]) from the ImagePlus's pixel array (JNA)
 *   tiff_read  ij.io.Opener.openImage of the file just written (a result coming back as TIFF)
 *   shm_to_short_array  block -> new short[] (a result coming back through shared memory)
 *   shm_mmap   JDK-only MappedByteBuffer over a file in /dev/shm
 * Args: side count scratchDir. Image = side x side uint16 (side 16384 = 512 MiB). One short[] per plane, like ImageJ.
 */
public class FijiExportBench {
    public static void main(String[] a) throws Exception {
        int side = Integer.parseInt(a[0]);
        int repeats = Integer.parseInt(a[1]);
        File scratch = new File(a[2]);
        short[] pixels = new short[side * side];
        Random r = new Random(1);
        for (int i = 0; i < pixels.length; i += 7) pixels[i] = (short) r.nextInt(65536);
        ImagePlus imp = new ImagePlus("bench", new ShortProcessor(side, side, pixels, null));
        long nbytes = (long) pixels.length * 2;
        for (int k = 0; k < repeats; k++) {
            StringBuilder out = new StringBuilder("{\"MiB\":" + nbytes / (1024 * 1024));
            File tif = new File(scratch, "fiji_bench.tif");
            long t = System.nanoTime();
            new FileSaver(imp).saveAsTiff(tif.getPath());
            out.append(",\"tiff_disk_s\":").append(sec(t));
            t = System.nanoTime();
            ImagePlus back = new ij.io.Opener().openImage(tif.getPath());     // what the Fiji host does with an image result
            out.append(",\"tiff_read_s\":").append(sec(t));
            if (back == null || back.getWidth() != side) throw new IllegalStateException("read back failed");
            t = System.nanoTime();
            org.apposed.appose.SharedMemory rb = org.apposed.appose.SharedMemory.create((long) side * side * 2);
            rb.buf(0, (long) side * side * 2).order(ByteOrder.nativeOrder()).asShortBuffer().put((short[]) pixels);   // stand-in for the worker's block
            double rbMake = (System.nanoTime() - t) / 1e9;
            t = System.nanoTime();
            short[] copy = new short[side * side];
            rb.buf(0, (long) side * side * 2).order(ByteOrder.nativeOrder()).asShortBuffer().get(copy);                 // block -> ImageJ short[]
            out.append(",\"shm_to_short_array_s\":").append(sec(t));
            rb.close();
            back.close();
            tif.delete();
            File tif2 = new File("/dev/shm/fiji_bench.tif");
            t = System.nanoTime();
            new FileSaver(imp).saveAsTiff(tif2.getPath());
            out.append(",\"tiff_shmfs_s\":").append(sec(t));
            tif2.delete();
            t = System.nanoTime();
            org.apposed.appose.SharedMemory shm = org.apposed.appose.SharedMemory.create(nbytes);
            shm.buf(0, nbytes).order(ByteOrder.nativeOrder()).asShortBuffer().put((short[]) imp.getProcessor().getPixels());
            out.append(",\"shm_appose_s\":").append(sec(t));
            shm.close();
            File f = new File("/dev/shm/fiji_bench_map");
            t = System.nanoTime();
            RandomAccessFile raf = new RandomAccessFile(f, "rw");
            raf.setLength(nbytes);
            MappedByteBuffer buf = raf.getChannel().map(FileChannel.MapMode.READ_WRITE, 0, nbytes);
            buf.order(ByteOrder.nativeOrder()).asShortBuffer().put((short[]) imp.getProcessor().getPixels());
            out.append(",\"shm_mmap_s\":").append(sec(t));
            raf.close();
            f.delete();
            System.out.println(out.append("}"));
        }
    }

    static String sec(long t0) { return String.format("%.3f", (System.nanoTime() - t0) / 1e9); }
}

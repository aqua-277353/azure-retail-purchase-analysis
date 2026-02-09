import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.HashSet;
import java.util.concurrent.TimeUnit;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.mapreduce.lib.output.MultipleOutputs;
import org.apache.hadoop.mapreduce.lib.output.TextOutputFormat;

public class MultiTableJob {

    // Định dạng ngày tháng
    private static final SimpleDateFormat parser = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
    private static final Calendar calendar = Calendar.getInstance();

    // Giả sử ngày "hôm nay" để tính 'số ngày kể từ lần cuối mua'
    private static final String TODAY_STRING = "2011-12-10 00:00:00";

    /**
     * MAPPER :
     * 1. Ghi Bảng 1 (Chi tiết) với cấu trúc cột MỚI bằng MultipleOutputs.
     * 2. Gửi dữ liệu (gắn thẻ CUST_) cho Reducer để xử lý Bảng 2.
     * 3. Gửi dữ liệu (gắn thẻ INV_) cho Reducer để xử lý Bảng 3.
    */
    public static class TransactionMapper extends Mapper<LongWritable, Text, Text, Text> {

        private MultipleOutputs<Text, Text> mo;
        private Text outputKey = new Text();
        private Text outputValue = new Text();

        @Override
        protected void setup(Context context) {
            mo = new MultipleOutputs<Text, Text>(context);
        }

        @Override
        public void map(LongWritable key, Text value, Context context) throws IOException, InterruptedException {
            String line = value.toString();
            // Bỏ qua dòng header
            if (key.get() == 0 && line.startsWith("InvoiceNo")) {
                String table1Header = "InvoiceNo,StockCode,Description,Quantity,Year,Month,Day,Hour,UnitPrice,CustomerID,Country,TotalAmount";

                // (loại có 3 tham số) là generic độc lập.
                mo.write("table1", NullWritable.get(), new Text(table1Header));
                return;
            }

            try {
                String[] cols = line.split(",");
                if (cols.length < 8) return; 

                String invoiceNo = cols[0];
                String stockCode = cols[1];   
                String description = cols[2]; 
                String quantityStr = cols[3];
                String dateString = cols[4];
                String unitPriceStr = cols[5];
                String customerID = cols[6];
                String country = cols[7];

                double quantity = Double.parseDouble(quantityStr);
                double unitPrice = Double.parseDouble(unitPriceStr);
                double totalAmount = quantity * unitPrice;

                Date date = parser.parse(dateString);
                calendar.setTime(date);
                int year = calendar.get(Calendar.YEAR);
                int month = calendar.get(Calendar.MONTH) + 1;
                int day = calendar.get(Calendar.DAY_OF_MONTH);
                int hour = calendar.get(Calendar.HOUR_OF_DAY);

                // --- 1. Ghi Bảng 1 (Chi tiết) ---
                String table1Line = String.format("%s,%s,%s,%s,%d,%d,%d,%d,%s,%s,%s,%.2f",
                        invoiceNo, stockCode, description, quantityStr,
                        year, month, day, hour,          
                        unitPriceStr, customerID, country, totalAmount); 

                mo.write("table1", NullWritable.get(), new Text(table1Line));
                
                // --- 2. Gửi dữ liệu cho Bảng 2 (Khách hàng) ---
                outputKey.set("CUST_" + customerID);
                outputValue.set(totalAmount + "," + invoiceNo + "," + dateString + "," + country);
                context.write(outputKey, outputValue);

                // --- 3. Ghi dữ liệu cho Bảng 3 (Hóa đơn) ---
                outputKey.set("INV_" + invoiceNo);
                outputValue.set(quantityStr + "," + totalAmount + "," + customerID + "," + country + "," + dateString);
                context.write(outputKey, outputValue);

            } catch (Exception e) {
                System.err.println("Lỗi Mapper: " + e.getMessage() + " | Dòng: " + line);
            }
        }
        
        @Override
        protected void cleanup(Context context) throws IOException, InterruptedException {
            mo.close();
        }
    }

    public static class AggregationReducer extends Reducer<Text, Text, NullWritable, Text> {

        private MultipleOutputs<NullWritable, Text> mo;
        private Date today;

        @Override
        protected void setup(Context context) {
            mo = new MultipleOutputs<NullWritable, Text>(context);
            try {
                today = parser.parse(TODAY_STRING);
            } catch (Exception e) {
                today = new Date(); 
            }
        }

        @Override
        public void reduce(Text key, Iterable<Text> values, Context context) throws IOException, InterruptedException {
            String keyString = key.toString();

            try {
                // --- Xử lý Bảng 2 (Khách hàng) ---
                if (keyString.startsWith("CUST_")) {
                    String customerID = keyString.substring(5);
                    double totalValue = 0;
                    HashSet<String> uniqueInvoices = new HashSet<>();
                    Date latestPurchaseDate = null;
                    String country = ""; 

                    for (Text val : values) {
                        String[] parts = val.toString().split(",");
                        double itemTotal = Double.parseDouble(parts[0]);
                        String invoiceNo = parts[1];
                        Date purchaseDate = parser.parse(parts[2]);
                        country = parts[3];

                        totalValue += itemTotal;
                        uniqueInvoices.add(invoiceNo);

                        if (latestPurchaseDate == null || purchaseDate.after(latestPurchaseDate)) {
                            latestPurchaseDate = purchaseDate;
                        }
                    }
                    
                    int totalPurchases = uniqueInvoices.size();
                    double avgPurchaseValue = (totalPurchases > 0) ? (totalValue / totalPurchases) : 0;

                    long daysSinceLastPurchase = 0;
                    if (latestPurchaseDate != null) {
                         long diffInMillis = Math.abs(today.getTime() - latestPurchaseDate.getTime());
                         daysSinceLastPurchase = TimeUnit.DAYS.convert(diffInMillis, TimeUnit.MILLISECONDS);
                    }

                    String table2Line = String.format("%s,%s,%d,%.2f,%d,%.2f",
                            customerID, country, totalPurchases, totalValue, daysSinceLastPurchase, avgPurchaseValue);
                    mo.write("table2", NullWritable.get(), new Text(table2Line));

                } 
                // --- Xử lý Bảng 3 (Hóa đơn) ---
                else if (keyString.startsWith("INV_")) {
                    String invoiceNo = keyString.substring(4);
                    double totalInvoiceValue = 0;
                    double totalInvoiceProducts = 0;
                    
                    String customerID = "";
                    String country = "";
                    String dateString = "";
                    
                    for (Text val : values) {
                        String[] parts = val.toString().split(",");
                        totalInvoiceProducts += Double.parseDouble(parts[0]);
                        totalInvoiceValue += Double.parseDouble(parts[1]);
                        
                        customerID = parts[2];
                        country = parts[3];
                        dateString = parts[4]; 
                    }

                    Date date = parser.parse(dateString);
                    calendar.setTime(date);
                    int year = calendar.get(Calendar.YEAR);
                    int month = calendar.get(Calendar.MONTH) + 1;
                    int day = calendar.get(Calendar.DAY_OF_MONTH);
                    int hour = calendar.get(Calendar.HOUR_OF_DAY);

                    String table3Line = String.format("%s,%.2f,%.0f,%s,%s,%d,%d,%d,%d",
                            invoiceNo, totalInvoiceValue, totalInvoiceProducts, customerID, country, year, month, day, hour);
                    mo.write("table3", NullWritable.get(), new Text(table3Line));
                }
            } catch (Exception e) {
                System.err.println("Lỗi Reducer: " + e.getMessage() + " | Key: " + keyString);
            }
        }

        @Override
        protected void cleanup(Context context) throws IOException, InterruptedException {
            mo.close();
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Sử dụng: MultiTableJob <input_path> <output_path>");
            System.exit(-1);
        }

        Configuration conf = new Configuration();
        Job job = Job.getInstance(conf, "Multi Table Generation Job");

        job.setJarByClass(MultiTableJob.class);
        job.setMapperClass(TransactionMapper.class);
        job.setReducerClass(AggregationReducer.class);

        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(Text.class);

        job.setOutputKeyClass(NullWritable.class);
        job.setOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(args[0]));
        FileOutputFormat.setOutputPath(job, new Path(args[1]));

        job.setNumReduceTasks(1); 

        MultipleOutputs.addNamedOutput(job, "table1", TextOutputFormat.class, NullWritable.class, Text.class);
        MultipleOutputs.addNamedOutput(job, "table2", TextOutputFormat.class, NullWritable.class, Text.class);
        MultipleOutputs.addNamedOutput(job, "table3", TextOutputFormat.class, NullWritable.class, Text.class);

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
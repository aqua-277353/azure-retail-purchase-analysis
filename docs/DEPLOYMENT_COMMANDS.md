### Step-by-Step Deployment

#### 1. Setup Azure Infrastructure
```bash
# Create Resource Group
az group create --name rg-retail-analytics --location southeastasia

# Create Storage Account with Data Lake Gen2
az storage account create \
  --name sadataretail \
  --resource-group rg-retail-analytics \
  --kind StorageV2 \
  --hns true \
  --sku Standard_LRS

# Create containers
az storage container create --name input-data --account-name sadataretail
az storage container create --name processed-data --account-name sadataretail
az storage container create --name models --account-name sadataretail

# Create Managed Identity for secure access
az identity create --name id-hdinsight --resource-group rg-retail-analytics
```

#### 2. Deploy Databricks Workspace
```bash
# Provision Databricks workspace
az databricks workspace create \
  --resource-group rg-retail-analytics \
  --name dbw-etl-pipeline \
  --location southeastasia \
  --sku standard

# Launch workspace & create cluster via UI
  -- Cluster name: etl-cluster
  -- Databricks Runtime: 12.2 LTS (Spark 3.3.2)
  -- Node type: Standard_DS3_v2 (2 workers)
  -- Auto-termination: 20 minutes
```

#### 3. Upload & Execute ETL Notebook
```python
# In Databricks Notebook
# Mount ADLS Gen2
configs = {
  "fs.azure.account.key.<storage-account>.dfs.core.windows.net": "<access-key>"
}
dbutils.fs.mount(
  source = "abfss://input-data@<storage-account>.dfs.core.windows.net/",
  mount_point = "/mnt/input",
  extra_configs = configs
)

# Run ETL job (see notebook code in Tien_xu_ly.ipynb)
%run /Workspace/Shared/etl_preprocessing
```

#### 4. Deploy HDInsight Cluster
```bash
# Create HDInsight cluster with Managed Identity
az hdinsight create \
  --name hdinsight-mapreduce \
  --resource-group rg-retail-analytics \
  --type hadoop \
  --version 4.0 \
  --headnode-size Standard_D13_v2 \
  --workernode-size Standard_D13_v2 \
  --workernode-count 2 \
  --storage-account sadataretail \
  --assign-identity id-hdinsight \
  --ssh-user sshuser \
  --ssh-password <secure-password>

# Build & deploy MapReduce JAR
cd /mapreduce-jobs/java
mvn clean package
az storage blob upload \
  --account-name sadataretail \
  --container-name jars \
  --name MultiTableJob-1.0.jar \
  --file target/MultiTableJob-1.0.jar
```

#### 5. Execute MapReduce Jobs
```bash
# SSH into HDInsight head node
ssh sshuser@hdinsight-mapreduce-ssh.azurehdinsight.net

# Download JAR to local VM
sudo -u hdfs hdfs dfs -get \
  abfs://<container>@sadataretail.dfs.core.windows.net/jars/MultiTableJob-1.0.jar \
  /tmp/MultiTableJob-1.0.jar

# Run MapReduce job
sudo -u hdfs hadoop jar /tmp/MultiTableJob-1.0.jar \
  "abfs://<container>@sadataretail.dfs.core.windows.net/processed-data/input.csv" \
  "abfs://<container>@sadataretail.dfs.core.windows.net/multi_output"

# Clean output directory for re-runs
sudo -u hdfs hdfs dfs -rm -r abfs://<container>@sadataretail.dfs.core.windows.net/multi_output
```

#### 6. Train & Deploy ML Model
```bash
# Create Azure ML Workspace
az ml workspace create \
  --name mlw-customer-segmentation \
  --resource-group rg-retail-analytics

# In Azure ML Studio:
1. Create Dataset from ADLS Gen2 (customers RFM data)
2. Create Compute Instance (Standard_DS2_v2)
3. Upload & run notebook: /notebooks/kmeans_training.ipynb
4. Register model: kmeans_model.pkl + scaler.pkl

# Create custom environment
az ml environment create --file environment.yml

# Deploy managed endpoint
az ml online-endpoint create --name ep-customer-prediction
az ml online-deployment create \
  --endpoint-name ep-customer-prediction \
  --model kmeans_model:1 \
  --environment kmeans-env:1 \
  --instance-type Standard_DS2_v2 \
  --instance-count 1
```

#### 7. Setup Power BI Dashboards
```powershell
# In Power BI Desktop
1. Get Data → Azure → Azure Data Lake Storage Gen2
2. Enter ADLS Gen2 endpoint URL
3. Authenticate with Azure AD or Access Key
4. Load datasets: customers, order_details, invoices
5. Create relationships & build visuals
6. Publish to Power BI Service
```

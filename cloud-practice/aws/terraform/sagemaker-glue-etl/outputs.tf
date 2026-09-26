output "bucket_name" {
  value       = aws_s3_bucket.data.bucket
  description = "Data lake bucket (raw/, curated/, rejected/, scripts/, tmp/)."
}

output "raw_path" {
  value       = local.raw_path
  description = "Drop new CSVs here, then re-run the job."
}

output "curated_path" {
  value       = local.curated_path
  description = "Partitioned Parquet written by the Glue job — the SageMaker training/feature input."
}

output "glue_job_name" {
  value       = aws_glue_job.etl.name
  description = "Glue ETL job."
}

output "glue_crawler_name" {
  value       = aws_glue_crawler.curated.name
  description = "Crawler that registers the curated table in the catalog."
}

output "glue_database_name" {
  value       = aws_glue_catalog_database.this.name
  description = "Glue Data Catalog database."
}

output "sagemaker_role_arn" {
  value       = aws_iam_role.sagemaker.arn
  description = "SageMaker execution role — reuse it for training jobs / processing jobs on the curated data."
}

output "notebook_instance_name" {
  value       = one(aws_sagemaker_notebook_instance.this[*].name)
  description = "Notebook instance name (null if create_notebook_instance = false)."
}

output "next_steps" {
  value = <<-EOT
    1. Run the ETL job:
         aws glue start-job-run --job-name ${aws_glue_job.etl.name}
    2. Watch it:
         aws glue get-job-runs --job-name ${aws_glue_job.etl.name} --max-items 1
       (on SUCCEEDED the conditional trigger starts the crawler automatically)
    3. Inspect the results:
         aws s3 ls ${local.curated_path} --recursive
         aws s3 ls ${local.rejected_path} --recursive
         aws glue get-tables --database-name ${aws_glue_catalog_database.this.name}
    4. Open the notebook (if created) and read the curated data:
         aws sagemaker create-presigned-notebook-instance-url --notebook-instance-name ${local.name}-notebook
         # in a notebook cell:
         #   import pandas as pd
         #   df = pd.read_parquet("${local.curated_path}")   # needs s3fs + pyarrow (preinstalled in the conda_python3 kernel)
    5. STOP THE METER when idle:
         aws sagemaker stop-notebook-instance --notebook-instance-name ${local.name}-notebook
  EOT
}

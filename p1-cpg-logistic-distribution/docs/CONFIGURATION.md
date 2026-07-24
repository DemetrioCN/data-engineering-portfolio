## Configure local credentials

This project uses Databricks CLI, Databricks Connect, and Terraform. All three share the
same authentication — there's no need to configure separate tokens for each tool.

### 1. Databricks CLI

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

This command automatically opens a tab in your default web browser, where you log in with
your Databricks credentials. On success, an OAuth credential is saved automatically on your
system in `~/.databrickscfg`.

Verify everything is set up:

```bash
databricks current-user me
```

### 2. Databricks Connect

With your virtual environment activated, install Databricks Connect:

```bash
pip3 install --upgrade "databricks-connect==17.3.*"  # or X.Y.* to match your cluster version
```

For the Enterprise tier, it's important that the Databricks Connect version matches your
cluster's runtime version. For Free Edition (serverless-only), this doesn't apply — there's
no fixed cluster runtime to match, just keep the package reasonably up to date.

Connection test:

```python
from databricks.connect import DatabricksSession
spark = DatabricksSession.builder.getOrCreate()
print(spark.range(5).collect())
```

### 3. Terraform

Terraform doesn't need separate credentials either — it automatically uses the same
`~/.databrickscfg`. Verify this as follows:

```bash
cd infra/databricks
terraform init
terraform plan
```

### Notes

- Never commit `~/.databrickscfg` or a `.env` file containing credentials.
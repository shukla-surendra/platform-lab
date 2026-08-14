# 1. Setup: Indexing PDFs from Blob Storage

> Assumes the concepts in [Overview](index.md) — Index, Indexer, Skillset,
> and why a skillset exists — are already familiar.

Goal: same end state `rag_pgvector_local` reaches by hand — a
container of PDFs made searchable and vector-enabled — but built as
four Azure resources instead of a Python ingestion script.

**One nuance before starting:** Azure AI Search's indexer has a
built-in PDF parser (Apache Tika–based "document cracking") that
extracts embedded text automatically into `/document/content` — you
only need the OCR skill for **scanned/image-only PDFs** with no text
layer. Most PDFs don't need it. The steps below include it, but treat
it as optional per your corpus.

## Step 0 — Prerequisites

- An **Azure AI Search** resource (Basic tier or above — semantic/
  vector features need Basic+).
- A **Storage Account** with a Blob container holding the PDFs.
- (Only if generating embeddings in the skillset) an **Azure OpenAI**
  resource with an embedding model deployed, e.g. `text-embedding-3-small`.
- The Python SDK: `pip install azure-search-documents azure-identity`.

```python
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient

endpoint = "https://<your-search-service>.search.windows.net"
credential = AzureKeyCredential("<admin-key>")

index_client = SearchIndexClient(endpoint, credential)
indexer_client = SearchIndexerClient(endpoint, credential)
```

## Step 1 — Connect the data source (point at the Blob container)

The indexer can't pull anything without this resource existing first.

```json
{
  "name": "docs-blob-datasource",
  "type": "azureblob",
  "credentials": { "connectionString": "<storage-account-connection-string>" },
  "container": { "name": "pdf-container" }
}
```

```python
from azure.search.documents.indexes.models import SearchIndexerDataSourceConnection, SearchIndexerDataContainer

data_source = SearchIndexerDataSourceConnection(
    name="docs-blob-datasource",
    type="azureblob",
    connection_string="<storage-account-connection-string>",
    container=SearchIndexerDataContainer(name="pdf-container"),
)
indexer_client.create_data_source_connection(data_source)
```

## Step 2 — Define the index schema

The fields queries will actually run against — same role as
`rag_pgvector_local/schema.sql`.

```json
{
  "name": "docs-index",
  "fields": [
    { "name": "id", "type": "Edm.String", "key": true },
    { "name": "content", "type": "Edm.String", "searchable": true },
    { "name": "contentVector", "type": "Collection(Edm.Single)",
      "dimensions": 1536, "vectorSearchProfile": "default-profile" },
    { "name": "metadata_storage_path", "type": "Edm.String", "filterable": true }
  ],
  "vectorSearch": {
    "profiles": [{ "name": "default-profile", "algorithm": "hnsw-config" }],
    "algorithms": [{ "name": "hnsw-config", "kind": "hnsw" }]
  }
}
```

```python
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    SearchFieldDataType, VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration,
)

index = SearchIndex(
    name="docs-index",
    fields=[
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=1536, vector_search_profile_name="default-profile"),
        SimpleField(name="metadata_storage_path", type=SearchFieldDataType.String, filterable=True),
    ],
    vector_search=VectorSearch(
        profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="hnsw-config")],
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
    ),
)
index_client.create_index(index)
```

## Step 3 — Define the skillset (chunk → embed, OCR only if scanned)

```json
{
  "name": "docs-skillset",
  "skills": [
    { "@odata.type": "#Microsoft.Skills.Vision.OcrSkill",
      "context": "/document/normalized_images/*",
      "inputs": [{ "name": "image", "source": "/document/normalized_images/*" }],
      "outputs": [{ "name": "text", "targetName": "ocrText" }] },

    { "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "context": "/document",
      "textSplitMode": "pages",
      "maximumPageLength": 2000,
      "inputs": [{ "name": "text", "source": "/document/content" }],
      "outputs": [{ "name": "textItems", "targetName": "chunks" }] },

    { "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
      "context": "/document/chunks/*",
      "resourceUri": "https://<aoai-resource>.openai.azure.com",
      "deploymentId": "text-embedding-3-small",
      "inputs": [{ "name": "text", "source": "/document/chunks/*" }],
      "outputs": [{ "name": "embedding", "targetName": "contentVector" }] }
  ]
}
```

This is the managed-service analogue of `chunking.py` + `embeddings.py`
— same two steps, split then embed, run inside Azure's pipeline
instead of a Python loop you own. Drop the OCR skill entirely if your
PDFs already have a text layer.

```python
from azure.search.documents.indexes.models import (
    SearchIndexerSkillset, OcrSkill, SplitSkill, AzureOpenAIEmbeddingSkill, InputFieldMappingEntry, OutputFieldMappingEntry,
)

skillset = SearchIndexerSkillset(
    name="docs-skillset",
    skills=[
        OcrSkill(context="/document/normalized_images/*",
                 inputs=[InputFieldMappingEntry(name="image", source="/document/normalized_images/*")],
                 outputs=[OutputFieldMappingEntry(name="text", target_name="ocrText")]),
        SplitSkill(context="/document", text_split_mode="pages", maximum_page_length=2000,
                   inputs=[InputFieldMappingEntry(name="text", source="/document/content")],
                   outputs=[OutputFieldMappingEntry(name="textItems", target_name="chunks")]),
        AzureOpenAIEmbeddingSkill(context="/document/chunks/*",
                                   resource_uri="https://<aoai-resource>.openai.azure.com",
                                   deployment_id="text-embedding-3-small",
                                   inputs=[InputFieldMappingEntry(name="text", source="/document/chunks/*")],
                                   outputs=[OutputFieldMappingEntry(name="embedding", target_name="contentVector")]),
    ],
)
indexer_client.create_skillset(skillset)
```

## Step 4 — Create the indexer (ties Data Source + Skillset + Index together)

If you kept the OCR skill, the indexer needs `imageAction` turned on
so PDFs get rasterized into `/document/normalized_images/*` for OCR to
read — without this parameter, the OCR skill's context is always empty
even for scanned PDFs.

```json
{
  "name": "docs-indexer",
  "dataSourceName": "docs-blob-datasource",
  "targetIndexName": "docs-index",
  "skillsetName": "docs-skillset",
  "schedule": { "interval": "PT1H" },
  "parameters": {
    "configuration": {
      "dataToExtract": "contentAndMetadata",
      "imageAction": "generateNormalizedImages"
    }
  },
  "outputFieldMappings": [
    { "sourceFieldName": "/document/chunks/*/contentVector",
      "targetFieldName": "contentVector" }
  ]
}
```

```python
from azure.search.documents.indexes.models import SearchIndexer, IndexingParameters, IndexingParametersConfiguration, FieldMapping

indexer = SearchIndexer(
    name="docs-indexer",
    data_source_name="docs-blob-datasource",
    target_index_name="docs-index",
    skillset_name="docs-skillset",
    parameters=IndexingParameters(configuration=IndexingParametersConfiguration(
        data_to_extract="contentAndMetadata",
        image_action="generateNormalizedImages",
    )),
    output_field_mappings=[
        FieldMapping(source_field_name="/document/chunks/*/contentVector", target_field_name="contentVector"),
    ],
)
indexer_client.create_indexer(indexer)
```

Creating the indexer runs it immediately once; the `schedule` governs
subsequent runs.

## Step 5 — Run and monitor

```python
indexer_client.run_indexer("docs-indexer")   # trigger an out-of-schedule run

status = indexer_client.get_indexer_status("docs-indexer")
print(status.last_result.status)              # "success" / "transientFailure" / "reset"
print(status.last_result.item_count, status.last_result.failed_item_count)
```

A `failed_item_count > 0` means specific documents errored (bad PDF,
OCR timeout, embedding call throttled) — `status.last_result.errors`
lists them per-document rather than failing the whole run.

## Step 6 — Query and verify

Same shape as this repo's `search.py`:

```python
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

search_client = SearchClient(endpoint, "docs-index", credential)

results = search_client.search(
    search_text="what is the refund policy",
    vector_queries=[VectorizedQuery(
        vector=query_embedding, k_nearest_neighbors=5, fields="contentVector"
    )],
    select=["content", "metadata_storage_path"],
)
```

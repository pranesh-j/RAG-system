# Image Processing System - API Documentation

## Overview

This document provides detailed specifications for the Image Processing System's API endpoints. The system processes image data from CSV files, compresses images, and provides access to the processed results.

## Base URL

```
http://localhost:5000/api
```

## API Endpoints

### 1. Upload CSV

Uploads a CSV file containing product data and image URLs for processing.

| Property | Value |
|----------|-------|
| Endpoint | `/upload` |
| Method | `POST` |
| Content-Type | `multipart/form-data` |

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | CSV file with required columns |

#### CSV Format Requirements

The CSV file must include the following columns:
- `S. No.` - Serial number
- `Product Name` - Name of the product
- `Input Image Urls` - Comma-separated list of image URLs to process

#### Responses

**Success Response (201 Created)**

```json
{
  "request_id": "61f078fa-c81a-4f96-aa45-40880918db3a"
}
```

**Error Responses**

- **400 Bad Request**
  ```json
  {
    "error": "No file part"
  }
  ```
  ```json
  {
    "error": "No selected file"
  }
  ```
  ```json
  {
    "error": "CSV missing required columns"
  }
  ```
  ```json
  {
    "error": "Invalid file type. Only CSV files are allowed."
  }
  ```

### 2. Check Status

Checks the processing status of a request using the request ID.

| Property | Value |
|----------|-------|
| Endpoint | `/status/{request_id}` |
| Method | `GET` |

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| request_id | String | Yes | Unique ID returned from the upload endpoint |

#### Responses

**Success Response (200 OK)**

```json
{
  "request_id": "61f078fa-c81a-4f96-aa45-40880918db3a",
  "status": "COMPLETED",
  "progress": 100.0,
  "details": {
    "total": 2,
    "completed": 2,
    "failed": 0,
    "in_progress": 0
  },
  "created_at": "Fri, 01 Mar 2025 22:05:17 GMT",
  "updated_at": "Fri, 01 Mar 2025 22:05:30 GMT"
}
```

**Error Response (404 Not Found)**

```json
{
  "error": "Request not found"
}
```

### 3. Download Results

Downloads the processed results as a CSV file.

| Property | Value |
|----------|-------|
| Endpoint | `/download/{request_id}` |
| Method | `GET` |

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| request_id | String | Yes | Unique ID returned from the upload endpoint |

#### Responses

**Success Response (200 OK)**

Returns a CSV file with the following format:
```
S. No.,Product Name,Input Image Urls,Output Image Urls
1,SKU1,"https://picsum.photos/200/300,https://picsum.photos/200/301","https://www.public-image-output-300,https://www.public-image-output-301"
2,SKU2,"https://picsum.photos/201/300,https://picsum.photos/202/300","https://www.public-image-output-300,https://www.public-image-output-300"
```

**Error Responses**

- **404 Not Found**
  ```json
  {
    "error": "Request not found"
  }
  ```

- **400 Bad Request**
  ```json
  {
    "error": "Request processing not complete"
  }
  ```

- **500 Internal Server Error**
  ```json
  {
    "error": "Failed to generate CSV"
  }
  ```

### 4. Register Webhook (Bonus)

Registers a webhook URL to be notified when processing completes.

| Property | Value |
|----------|-------|
| Endpoint | `/webhook` |
| Method | `POST` |
| Content-Type | `application/json` |

#### Request Body

```json
{
  "request_id": "61f078fa-c81a-4f96-aa45-40880918db3a",
  "webhook_url": "https://webhook.example.com/callback"
}
```

#### Responses

**Success Response (200 OK)**

```json
{
  "message": "Webhook registered successfully"
}
```

**Error Responses**

- **400 Bad Request**
  ```json
  {
    "error": "Missing required fields: request_id and webhook_url"
  }
  ```

- **404 Not Found**
  ```json
  {
    "error": "Request not found"
  }
  ```

## Webhook Notification Format

When processing completes, the system will send a POST request to the registered webhook URL with the following payload:

```json
{
  "request_id": "61f078fa-c81a-4f96-aa45-40880918db3a",
  "status": "COMPLETED",
  "message": "Processing completed"
}
```

## Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - The request succeeded |
| 201 | Created - The resource was successfully created |
| 400 | Bad Request - Invalid input or parameters |
| 404 | Not Found - The requested resource does not exist |
| 500 | Internal Server Error - Server-side error |

## Processing Statuses

| Status | Description |
|--------|-------------|
| PENDING | Request received but processing has not started |
| PROCESSING | Images are currently being processed |
| COMPLETED | All images have been successfully processed |
| PARTIALLY_COMPLETED | Some images were processed successfully, others failed |
| FAILED | Processing failed completely |
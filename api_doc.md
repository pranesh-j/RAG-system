Let's continue with the Low-Level Design (LLD) document. This should explain the technical architecture of your system, component interactions, and data flow.

# Low-Level Design Document (low_level_design.md)

```markdown
# Image Processing System - Low-Level Design

## 1. System Architecture

The Image Processing System follows a distributed architecture with several components working together to provide efficient, asynchronous processing of images from CSV data.

![System Architecture Diagram](images/system_architecture.png)

### 1.1 Key Components

1. **Flask Web Application**
   - Serves API endpoints
   - Validates input data
   - Coordinates interactions between other components
   - Handles request and response formatting

2. **PostgreSQL Database**
   - Stores request metadata
   - Tracks processing status
   - Maintains relationships between requests and products
   - Persists both input and output image URLs

3. **Redis Message Broker**
   - Facilitates asynchronous task management
   - Queues image processing tasks
   - Provides task status tracking

4. **Celery Worker**
   - Executes background image processing
   - Updates processing status in the database
   - Triggers webhooks upon completion
   - Handles errors and partial failures

5. **Image Processing Service**
   - Downloads images from URLs
   - Compresses images to 50% quality
   - Creates temporary storage for processed files

## 2. Component Interactions

### 2.1 Request Flow

1. **CSV Upload and Validation**
   - Client uploads CSV file to Flask application
   - Application validates CSV format and content
   - Application creates database entries for the request and products
   - Application returns a unique request ID to the client

2. **Task Queuing**
   - Flask application sends the request ID to Celery via Redis
   - Celery worker picks up the task from the queue

3. **Image Processing**
   - Celery worker retrieves product data from the database
   - For each product and image URL:
     - Download the image
     - Compress using PIL/Pillow
     - Generate output URL
     - Update database with status and output URL
   - Worker updates overall request status

4. **Completion and Notification**
   - Upon completion, Celery worker updates request status in database
   - If webhook URL is registered, sends notification to the client
   - Client can retrieve completed data via the download endpoint

### 2.2 Sequence Diagram

```
Client          Flask App            Database           Redis           Celery Worker
  |                |                    |                 |                   |
  | Upload CSV     |                    |                 |                   |
  |--------------->|                    |                 |                   |
  |                | Validate           |                 |                   |
  |                |----------------    |                 |                   |
  |                |                |   |                 |                   |
  |                |<---------------    |                 |                   |
  |                | Create Request     |                 |                   |
  |                |------------------->|                 |                   |
  |                | Create Products    |                 |                   |
  |                |------------------->|                 |                   |
  | Return ID      |                    |                 |                   |
  |<---------------|                    |                 |                   |
  |                | Queue Task         |                 |                   |
  |                |------------------------------------ >|                   |
  |                |                    |                 | Dequeue Task      |
  |                |                    |                 |------------------>|
  |                |                    |                 |                   |
  |                |                    | Get Data        |                   |
  |                |                    |<------------------|                 |
  |                |                    |                 |                   |
  |                |                    |                 |                   | Process Images
  |                |                    |                 |                   |-------------
  |                |                    |                 |                   |            |
  |                |                    |                 |                   |<------------
  |                |                    | Update Status   |                   |
  |                |                    |<------------------|                 |
  |                |                    |                 |                   |
  | Check Status   |                    |                 |                   |
  |--------------->|                    |                 |                   |
  |                | Query Status       |                 |                   |
  |                |------------------->|                 |                   |
  | Return Status  |                    |                 |                   |
  |<---------------|                    |                 |                   |
  |                |                    |                 |                   |
  |                |                    |                 |                   | Completion
  |                |                    |                 |                   |-------------
  |                |                    | Update Final    |                   |            |
  |                |                    |<------------------|                 |<------------
  |                |                    |                 |                   |
  |                |                    |                 |                   | Send Webhook
  |                |                    |                 |                   |------------->
  |                |                    |                 |                   |
  | Download       |                    |                 |                   |
  |--------------->|                    |                 |                   |
  |                | Get Data           |                 |                   |
  |                |------------------->|                 |                   |
  | Return CSV     |                    |                 |                   |
  |<---------------|                    |                 |                   |
```

## 3. Data Flow

### 3.1 Upload Phase
1. Client submits CSV file
2. Flask validates and parses CSV
3. Request and product records created in database
4. Processing task queued in Redis

### 3.2 Processing Phase
1. Celery worker retrieves request data
2. For each product:
   - Updates status to "PROCESSING"
   - Downloads images from input URLs
   - Compresses images
   - Generates output URLs
   - Updates status to "COMPLETED" or "FAILED"
3. Overall request status updated

### 3.3 Retrieval Phase
1. Client queries status endpoint
2. When complete, client downloads processed data as CSV

## 4. Error Handling

### 4.1 Error Categories
1. **CSV Validation Errors**
   - Missing required columns
   - Invalid format
   - Empty file

2. **Processing Errors**
   - Image download failures
   - Image processing failures
   - Invalid image formats

3. **System Errors**
   - Database connection issues
   - Redis connection failures
   - Worker failures

### 4.2 Error Recovery
1. Per-product error isolation
   - Processing continues for other products if one fails
   - Failed products marked accordingly
   - Partially successful requests still produce usable output

2. Status reporting
   - Detailed status for each product
   - Overall request status reflects partial success

## 5. Technical Considerations

### 5.1 Scalability
- Horizontal scaling of Celery workers possible
- Database connection pooling for higher load
- Redis persistence for task reliability

### 5.2 Security
- Input validation prevents injection attacks
- Temporary file cleanup prevents disk space issues
- Cross-origin considerations for API endpoints

### 5.3 Performance
- Asynchronous processing allows handling multiple requests
- Individual product failures don't block entire requests
- Task queuing prevents server overload
```

This document covers the technical design of your system. Next, we can create the documentation for the asynchronous workers. Would you like me to proceed with that?

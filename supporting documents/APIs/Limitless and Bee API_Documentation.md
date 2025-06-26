# API Documentation for Multi-Source Data Ingestion

This document contains detailed API specifications for all data sources integrated into the awareable-md system.

## Table of Contents

1. [Limitless API](#limitless-api)
2. [Bee API](#bee-api)

---

## Limitless API

### Authentication
- **Method**: API Key in header
- **Header**: `x-api-key: {api_key}`
- **Base URL**: `https://api.limitless.ai`

### Endpoints
- **Lifelogs**: `GET /v1/lifelogs`

### Request Parameters
- `timezone`: IANA timezone specifier (default: UTC)
- `date`: Return entries for specific date (YYYY-MM-DD)
- `start`: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS)
- `end`: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS)
- `cursor`: Pagination cursor for next set of entries
- `direction`: Sort direction "asc" or "desc" (default: "desc")
- `includeMarkdown`: Include markdown content (default: true)
- `includeHeadings`: Include headings (default: true)
- `limit`: Maximum number of entries to return

### Response Format
```json
{
  "data": {
    "lifelogs": [
      {
        "id": "lifelog_id",
        "title": "Entry title from first heading1 node",
        "markdown": "Raw markdown content of the entry",
        "contents": [
          {
            "type": "heading1|heading2|heading3|blockquote|...",
            "content": "Content of the node",
            "startTime": "2025-05-24T01:36:53.875Z",
            "endTime": "2025-05-24T02:16:17.472Z",
            "startOffsetMs": 1680,
            "endOffsetMs": 4020,
            "children": [],
            "speakerName": "Speaker identifier",
            "speakerIdentifier": "user"
          }
        ]
      }
    ]
  },
  "meta": {
    "lifelogs": {
      "nextCursor": "pagination_cursor",
      "count": 10
    }
  }
}
```

### Key Data Structures

#### Lifelog Object
- **id**: Unique identifier for the entry
- **title**: Title equal to first heading1 node
- **markdown**: Raw markdown content (nullable)
- **contents**: Array of ContentNode objects

#### ContentNode Object
- **type**: Node type (heading1, heading2, heading3, blockquote, etc.)
- **content**: Text content of the node
- **startTime/endTime**: ISO datetime strings in given timezone
- **startOffsetMs/endOffsetMs**: Milliseconds after entry start
- **children**: Array of child ContentNode objects
- **speakerName**: Speaker identifier (nullable)
- **speakerIdentifier**: "user" when speaker identified as user (nullable)

### Sub-Sources
- **None** - Limitless is a single source

---

## Bee API

### Authentication
- **Method**: API Key in header
- **Header**: `x-api-key: {api_key}`
- **Base URL**: `https://api.bee.computer/v1/me`

### Available Endpoints
Each of the following require /v1/me prefix
- **Conversations**: `GET /conversations`
- Deleted Conversations: `DELETE /conversations/{id}`
- **Conversation Details**: `GET /conversations/{id}`
- **Facts**: `GET /facts`
- **Fact Details**: `GET /facts/{id}`
- Fact Deletion: `DELETE /facts/{id}`
- **Locations**: `GET /locations`
- **Todos**: `GET /todos`
- **Todo Details**: `GET /todos/{id}`
- Todo Deletion: `DELETE /todos/{id}`


### Conversations Endpoint

#### List Conversations
**Endpoint**: `GET /conversations`

**Response Format**:
```json
{
  "conversations": [
    {
      "id": 2257024,
      "start_time": "2025-05-24T01:36:53.875Z",
      "end_time": "2025-05-24T02:16:17.472Z",
      "device_type": "Bee",
      "summary": "<font color=\"#ff0000\">### Summary</font>\nBruce ..\n<font color=\"#ff0000\">### Atmosphere</font>\nThe tone of the conversation was casual and somewhat light-hearted, .. \n<font color=\"#ff0000\">### Action Items</font>\n- Consider implementing a consistent system or protocol for managing and checking simplifying language and settings changes on devices to reduce frustration for all family members involved. <font color=\"#ff0000\">### Key Takeaways</font>\n- **Daily Tasks**: Bruce confirmed his to-do list, focusing on buying distilled water",
      "short_summary": "Discussion on Computer and Language Changes",
      "state": "COMPLETED",
      "created_at": "2025-05-24T01:36:53.875Z",
      "updated_at": "2025-05-24T02:16:17.472Z",
      "primary_location": {
        "address": "6027 Willow Glen Dr, Wilmington, NC, New Hanover County, 28412, United States",
        "latitude": 34.12126698379628,
        "longitude": -77.91256861025497,
        "created_at": "2025-05-24T01:57:14.542Z"
      }
    }
  ]
}
```

### Conversation Details Endpoint

When calling the endpoint to fetch the details of a single conversation using `/conversations/{id}`, the API returns a JSON object (note: not an array) containing the key `"conversation"`. This object provides detailed conversation data, including an overview of the conversation and additional data fields not present when fetching the list of conversations.

**Response Structure:**

```json
{
  "conversation": {
    "id": 2697282,
    "start_time": "2025-06-08T21:58:04.273Z",
    "end_time": "2025-06-08T22:40:08.851Z",
    "device_type": "Bee",
    "summary": "Here's a summary of y...",
    "short_summary": "Home life, family, and chores",
    "state": "COMPLETED",
    "created_at": "2025-06-08T21:58:04.273Z",
    "updated_at": "2025-06-08T22:40:08.851Z",
    "primary_location": {
      "address": "6027 Willow Glen Dr, Wilmington, NC, ...",
      "latitude": 34.12126698379628,
      "longitude": -77.91256861025497,
      "created_at": "2025-06-08T21:57:14.542Z"
    },
    "transcriptions": [
      {
        "id": 3809926,
        "realtime": true,
        "utterances": [
          {
            "id": 726113178,
            "realtime": true,
            "start": 73.07,
            "end": 73.57,
            "spoken_at": "2025-06-08T21:59:19.593Z",
            "text": "Hey.",
            "speaker": "1",
            "created_at": "2025-06-08T21:59:20.113Z"
          },
          {
            "id": 726114109,
            "realtime": true,
            "start": 80.76,
            "end": 83.5,
            "spoken_at": "2025-06-08T21:59:27.283Z",
            "text": "Was super, super, super slow.",
            "speaker": "1",
            "created_at": "2025-06-08T21:59:29.062Z"
          }
          // ... additional utterances
        ]
      }
      // ... additional transcriptions
    ]
  }
}
```

**Key Points About Conversation Details:**
- The endpoint returns a single **conversation** object (singular), not an array of conversations
- The top-level key in the response is `"conversation"` (singular), not "conversations" (plural)
- Contains both overview data (summaries, timestamps, location) and detailed transcription data
- The **transcriptions** array contains one or more transcription objects
- Each transcription contains an **utterances** array with individual speech segments
- **utterances** represent the actual speech-to-text chat content with timing information
- **speaker** identifiers differentiate between participants in the conversation
- **start/end** fields show timing in seconds from conversation start
- **spoken_at** provides absolute timestamp of when words were spoken

**Usage Notes:**
1. First query `/conversations` to get a list of conversation IDs
2. Then fetch detailed data with `/conversations/{id}` for conversations of interest
3. The summaries contain structured markdown with sections that can be parsed
4. Utterances can be used to reconstruct the full conversation transcript with speaker attribution

### Facts Endpoint

**Endpoint**: `GET /facts`


### Locations Endpoint

**Endpoint**: `GET /locations`

**Response Format**:
```json
{
  "locations": [
    {
      "id": 64469922,
      "latitude": 34.12144474561337,
      "longitude": -77.91256852987196,
      "address": "6023 Willow Glen Dr, Wilmington, NC, New Hanover County, 28412, United States",
      "created_at": "2025-05-26T21:41:13.506Z"
    },
    {
      "id": 64469921,
      "latitude": 34.12144474561337,
      "longitude": -77.91256852987196,
      "address": "6023 Willow Glen Dr, Wilmington, NC, New Hanover County, 28412, United States",
      "created_at": "2025-05-26T21:41:13.505Z"
    },
    {
      "id": 64469920,
      "latitude": 34.12144474561337,
      "longitude": -77.91256852987196,
      "address": "6023 Willow Glen Dr, Wilmington, NC, New Hanover County, 28412, United States",
      "created_at": "2025-05-26T21:41:13.501Z"
    }
  ]
}
```

**Key Fields**:
- **id**: Unique identifier for the location entry
- **latitude**: Latitude coordinate (float)
- **longitude**: Longitude coordinate (float)
- **address**: Full address string
- **created_at**: ISO timestamp when the location was recorded

**Status**: ✅ **COMPLETE** - Response format documented

### Todos Endpoint

**Endpoint**: `GET /todos`

**Response Format**:
```json
{
  "todos": [
    {
      "id": 4780265,
      "text": "Bring Coke to work",
      "alarm_at": "2025-06-04T11:30:00.000Z",
      "completed": false,
      "created_at": "2025-06-02T20:04:22.173Z"
    }
  ]
}
```

**Key Fields**:
- **id**: Unique identifier for the todo entry
- **text**: Todo description (string)
- **alarm_at**: ISO timestamp for alarm/reminder (nullable)
- **completed**: Boolean indicating completion status
- **created_at**: ISO timestamp when the todo was created

**Status**: ✅ **COMPLETE** - Response format documented

---

## Implementation Notes

### Sub-Source Routing Strategy
The Bee adapter will:
1. Check `sub_source` parameter in `fetch_data()`
2. Route to appropriate endpoint:
   - `conversations` → `/conversations`
   - `facts` → `/facts`
   - `locations` → `/locations`
3. For conversation details, use the ID from list to fetch full content

### Content Processing Requirements
- **Clean Markdown Processing**: Content already in clean markdown format
- **Section Extraction**: Parse structured summary sections (Summary, Atmosphere, Key Takeaways, Action Items)
- **Transcript Processing**: Extract utterances from transcription arrays
- **Location Normalization**: Standardize location data format
- **Timestamp Handling**: Convert ISO strings to standard format

### Rate Limiting
- **Default**: 1 second delay between requests (following Limitless pattern)
- **Configurable**: Can be adjusted via configuration

### Error Handling
- **Network errors**: Graceful fallback with retry logic
- **Authentication errors**: Clear error messages
- **Data format errors**: Robust parsing with validation

---

Some key API details:
    - Limitless API paging strategy:
       - Cursor and count in metadata
         Example:
         "meta": {
                "lifelogs": {
                "nextCursor": "string",
                "count": 0
                }
            }
    - Bee API paging strategy:
            "currentPage": 1,
            "totalPages": 58,
            "totalCount": 579
    - Bee conversations arguments:
        - userId (default = 'me')
        - limit (default = 10)
        - page (default = 1)
        - Sub-source /conversations/id
            - useId (default = 'me')
            - id (conversationId), forgien key from /conversations response key/value id
    - Bee Locations arguments
      - userId (default = 'me')
      - limit (default = 10)
      - page (default = 1)
      - conversationId forgien key from /conversations response key/value id
    - Bee facts arguments
        - userId (default = 'me')
        - limit (default = 10)
        - page (default = 1)
        - confirmed (default = true)
    - Bee facts by id /facts/{id}
      - userId (default = 'me')
      - id
    - Bee todos arguments
      - userId (default = 'me')
      - limit (default = 10)
      - page (default = 1)


LIMITLESS openapi spec:


openapi: 3.0.3
info:
  title: Limitless Developer API
  description: API for accessing lifelogs, providing transparency and portability to user data.
  version: 1.0.0
servers:
  - url: https://api.limitless.ai/
    description: Production server

tags:
  - name: Lifelogs
    description: Operations related to lifelogs data

components:
  schemas:
    ContentNode:
      type: object
      properties:
        type:
          type: string
          description: Type of content node (e.g., heading1, heading2, heading3, blockquote, paragraph). More types might be added.
        content:
          type: string
          description: Content of the node.
        startTime:
          type: string
          format: date-time
          description: ISO format in given timezone.
        endTime:
          type: string
          format: date-time
          description: ISO format in given timezone.
        startOffsetMs:
          type: integer
          description: Milliseconds after start of this entry.
        endOffsetMs:
          type: integer
          description: Milliseconds after start of this entry.
        children:
          type: array
          items:
            $ref: "#/components/schemas/ContentNode"
          description: Child content nodes.
        speakerName:
          type: string
          description: Speaker identifier, present for certain node types (e.g., blockquote).
          nullable: true
        speakerIdentifier:
          type: string
          description: Speaker identifier, when applicable. Set to "user" when the speaker has been identified as the user.
          enum: ["user"]
          nullable: true

    Lifelog:
      type: object
      properties:
        id:
          type: string
          description: Unique identifier for the entry.
        title:
          type: string
          description: Title of the entry. Equal to the first heading1 node.
        markdown:
          type: string
          description: Raw markdown content of the entry.
          nullable: true
        contents:
          type: array
          items:
            $ref: "#/components/schemas/ContentNode"
          description: List of ContentNodes.
        startTime:
          type: string
          format: date-time
          description: ISO format in given timezone.
        endTime:
          type: string
          format: date-time
          description: ISO format in given timezone.
        isStarred:
          type: boolean
          description: Whether the lifelog has been starred by the user.
        updatedAt:
          type: string
          format: date-time
          description: The timestamp when the lifelog was last updated in ISO 8601 format.

    MetaLifelogs:
      type: object
      properties:
        nextCursor:
          type: string
          description: Cursor for pagination to retrieve the next set of lifelogs.
          nullable: true
        count:
          type: integer
          description: Number of lifelogs in the current response.

    Meta:
      type: object
      properties:
        lifelogs:
          $ref: "#/components/schemas/MetaLifelogs"

    LifelogsResponseData:
      type: object
      properties:
        lifelogs:
          type: array
          items:
            $ref: "#/components/schemas/Lifelog"

    LifelogsResponse:
      type: object
      properties:
        data:
          $ref: "#/components/schemas/LifelogsResponseData"
        meta:
          $ref: "#/components/schemas/Meta"

paths:
  /v1/lifelogs:
    get:
      operationId: getLifelogs
      summary: Returns a list of lifelogs.
      description: Returns a list of lifelogs based on specified time range or date.
      tags:
        - Lifelogs
      parameters:
        - in: query
          name: timezone
          schema:
            type: string
          description: IANA timezone specifier. If missing, UTC is used.
        - in: query
          name: date
          schema:
            type: string
            format: date
          description: Will return all entries beginning on a date in the given timezone (YYYY-MM-DD).
        - in: query
          name: start
          schema:
            type: string
            format: date-time
          description: Start datetime in modified ISO-8601 format (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS). Timezones/offsets will be ignored.
        - in: query
          name: end
          schema:
            type: string
            format: date-time
          description: End datetime in modified ISO-8601 format (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS). Timezones/offsets will be ignored.
        - in: query
          name: cursor
          schema:
            type: string
          description: Cursor for pagination to retrieve the next set of entries.
        - in: query
          name: direction
          schema:
            type: string
            enum: ["asc", "desc"]
            default: "desc"
          description: Sort direction for entries.
        - in: query
          name: includeMarkdown
          schema:
            type: boolean
            default: true
          description: Whether to include markdown content in the response.
        - in: query
          name: includeHeadings
          schema:
            type: boolean
            default: true
          description: Whether to include headings in the response.
        - in: query
          name: limit
          schema:
            type: integer
          description: Maximum number of entries to return.
        - in: query
          name: isStarred
          schema:
            type: boolean
            default: false
          description: When true, only starred lifelogs will be returned.

      responses:
        "200":
          description: Successful response with entries.
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/LifelogsResponse"

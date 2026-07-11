# Performance & Scalability Patterns Reference

This catalog details common performance bottlenecks, scalability issues, and their corresponding remediation strategies.

---

## 1. Database Optimization & Query Efficiency

### 1.1 The N+1 Query Problem
- **Symptom**: Executing a query to retrieve a list of records, and then executing another query for *each* record to fetch related data (e.g. fetching 100 posts, then running 100 queries to fetch the author of each post).
- **Risk**: Severe latency spikes, database connection starvation.
- **Remediation**: Use database joins or eager loading:
  - *Django*: Use `.select_related()` (for ForeignKey/OneToOne) or `.prefetch_related()` (for ManyToMany).
  - *SQLAlchemy*: Use `joinedload()` or `subqueryload()`.
  - *Node/Prisma*: Use `include` statements.

### 1.2 Missing Indexes
- **Symptom**: Sequential table scans (SeqScan) on filter/search fields, resulting in linear lookup times $O(N)$.
- **Risk**: Slow queries as table size grows.
- **Remediation**: Create indexes on fields frequently used in `WHERE`, `JOIN` (foreign keys), `ORDER BY`, and `GROUP BY` clauses. Use Composite Indexes for multi-column queries.
- **Caution**: Do not index fields with low cardinality (e.g., boolean fields) or tables with high write-to-read ratios, as every index slows down `INSERT`, `UPDATE`, and `DELETE`.

### 1.3 Connection Starvation
- **Symptom**: Creating and closing database connections for every HTTP request.
- **Risk**: High connection overhead latency; database reaches maximum connection limit.
- **Remediation**: Implement a Database Connection Pool (e.g., `PgBouncer` for Postgres, ORM built-in pooling).

---

## 2. Caching Strategies

### 2.1 Cache-Aside (Lazy Loading)
- **Pattern**: Application checks cache first. On miss, it queries the database, writes the result to the cache, and returns it.
- **Use Case**: Read-heavy workloads with data that doesn't change constantly (e.g., product details, user profiles).
- **Code Pattern**:
  ```python
  def get_user(user_id):
      user = cache.get(f"user:{user_id}")
      if not user:
          user = db.query_user(user_id)
          cache.set(f"user:{user_id}", user, expire=3600)
      return user
  ```

### 2.2 Write-Through / Write-Behind
- **Write-Through**: Application writes to cache and database simultaneously. Ensures consistency but increases write latency.
- **Write-Behind (Write-Back)**: Application writes to cache immediately, and a queue updates the database asynchronously. Extremely fast writes, but risk of data loss on cache crashes.

### 2.3 Cache Invalidation Strategies
- **Time-to-Live (TTL)**: Always set a reasonable expiration time.
- **Write-Invalidate**: Delete or update cache keys when the underlying database record is modified.
- **Avoid Cache Stampede**: Use mutex locks or calculate cache updates in the background before they expire.

---

## 3. Concurrency & Asynchronous Task Processing

### 3.1 Synchronous Blocking Operations
- **Symptom**: Handling heavy computations, PDF generation, or third-party API calls directly inside the HTTP request/response cycle.
- **Risk**: Slow response times (bad INP/LCP), request timeouts, and server blocking.
- **Remediation**: Use an asynchronous task queue (e.g. Celery with Redis/RabbitMQ, BullMQ for Node) to offload heavy tasks to background workers.
- **Flow**:
  `Client -> HTTP POST -> Queue Task -> HTTP 202 Accepted (Task ID) -> Background Worker processes task`

### 3.2 Thread/Process Pool Exhaustion
- **Symptom**: Web server becomes unresponsive under high load because all worker threads are waiting on network I/O.
- **Remediation**: Use asynchronous I/O frameworks (e.g. FastAPI/asyncio for Python, Node.js event-loop, Go channels) for I/O-bound tasks.

---

## 4. Architectural Scalability

### 4.1 Horizontal Scaling vs. Vertical Scaling
- **Vertical (Scale Up)**: Adding more CPU/RAM to a single server. Limits are quickly reached.
- **Horizontal (Scale Out)**: Adding more server nodes behind a Load Balancer (Nginx, HAProxy, Cloud Load Balancer). Requires stateless application design.

### 4.2 Database Replication & Partitioning
- **Read Replicas**: Direct read queries to read-only replicas, reserving the primary database node for writes.
- **Sharding (Horizontal Partitioning)**: Distribute rows across multiple database instances based on a shard key (e.g. user_id range).
- **Vertical Partitioning**: Splitting tables by columns (e.g., separating large text columns into another table).

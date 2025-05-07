# Section 9: Ongoing Monitoring Design

## 9.1 Performance Monitoring

The IRIS model will implement a comprehensive performance monitoring approach based on the successful quantitative evaluation methodology used during initial non-APG testing. Our strategy includes several key components.

### Quarterly Evaluation Using Original Test Set

A subset of 50 questions from the original model testing dataset of 100 questions will be evaluated quarterly. These questions will cover both APG and non-APG database queries to ensure comprehensive monitoring. Each question will be evaluated using the same structured approach as the initial testing, focusing on database selection accuracy (Did the system select the right database?), document selection accuracy (Did the system retrieve the relevant documents?), response quality (Overall scoring of the generated response), and detailed paragraph-level feedback and comments on specific issues. The test question subset used for ongoing monitoring is available in the SharePoint folder: `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/OngoingMonitoring/QuarterlyTestSet/`.

### Quantitative Scoring Approach

The same quantitative scoring methodology used in the initial non-APG testing will be applied. This includes the following baseline metrics and targets: Database Selection Accuracy (Baseline 99.4%, Target ≥ 95%), Document Selection Accuracy (Baseline 97.7%, Target ≥ 95%), Answer Accuracy (Baseline 94.2%, Target ≥ 90%), and Overall Performance Score (Baseline 89.6%, Target ≥ 85%). All results will be documented in standardized Excel templates for consistent evaluation. Tracking results over time will identify performance trends and potential degradation, ensuring direct comparability with baseline performance established during initial testing.

### LLM Judge Analysis and Aggregation

After manual scoring and commenting, results will be processed through an LLM judge. This judge will highlight major concerns based on reviewer comments, aggregate scores across different dimensions, generate a comprehensive analysis report with key insights, and identify potential patterns in model performance issues. This combined human-AI evaluation approach ensures both detailed human expert assessment and systematic analysis. Quarterly monitoring reports are stored in the SharePoint folder: `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/OngoingMonitoring/QuarterlyReports/`.

### Table 11: Model Performance Tracking Metrics

| Model ID | Metric # | Metric Category | Metric Description | Metric Threshold | Monitoring Frequency | Monitoring Accountable |
|----------|----------|-----------------|-------------------|------------------|---------------------|------------------------|
| IRIS-001 | PM-01    | Database Selection | Percentage of queries with correct database selection | ≥ 95% | Quarterly | Model Owner |
| IRIS-001 | PM-02    | Document Selection | Percentage of queries with correct document selection | ≥ 95% | Quarterly | Model Owner |
| IRIS-001 | PM-03    | Answer Accuracy    | Percentage accuracy of answer content | ≥ 90% | Quarterly | Model Owner |
| IRIS-001 | PM-04    | Overall Performance | Combined performance score across all dimensions | ≥ 85% | Quarterly | Model Owner |
| IRIS-001 | PM-05    | Edge Case Handling | Performance on edge case queries | ≥ 80% | Quarterly | Model Owner |
| IRIS-001 | PM-06    | User Feedback   | Aggregated positive feedback rate from Maven interface | ≥ 80% | Monthly | Model Owner |

### Real-World Question Incorporation

As the model operates in production, a selection of actual user questions will be collected through the Maven interface. These real-world questions will gradually supplement the original test set, ensuring evaluation remains relevant to actual usage patterns. Edge cases and complex queries encountered in production will be deliberately included in the evaluation set. Production user feedback from thumbs up/down interactions will also be incorporated into the monitoring analysis. APG team members will be involved in the quarterly reviews to ensure alignment with current accounting policies and standards.

## 9.2 Process Monitoring

IRIS implements comprehensive process monitoring through an automated system that tracks operational performance metrics across the entire query processing pipeline.

### Process Monitoring Database

The existing process monitor database (`process_monitor_logs`) will continue to be used for tracking detailed operational metrics. Each stage of query processing is logged with comprehensive performance data, including the Run UUID (unique identifier for each model invocation), stage name (router, clarifier, planner, database subagents, summarizer), timing metrics (start time, end time, duration), LLM call details (model used, prompt tokens, completion tokens, cost), decision details (key outputs from each stage), and status and error information. This data enables both real-time monitoring and historical performance analysis.

### Process Monitoring Analysis

Jupyter notebooks in the `/notebooks/` directory, particularly `process_monitor_analysis.ipynb`, provide visualization and statistical analysis of system performance metrics. These notebooks will be run on a monthly basis to identify trends in response times for different query types, token usage patterns, cost per query, error rates by component, and database usage frequency.

### Baseline Metrics Establishment

During initial Maven deployment, baseline process metrics will be established for different query types. These baselines will include expected response times, token usage ranges, and process flow patterns. Thresholds will be set based on these baselines to identify potential operational issues.

### Continuous Operational Monitoring

In production, all queries will be compared against baseline metrics. Automated alerts will trigger when metrics fall outside of established thresholds. Process monitoring notebook scripts enable detailed analysis of performance trends.

### Table 12: Process Monitoring Metrics

| Model ID | Metric # | Metric Category | Metric Description | Metric Threshold | Monitoring Frequency | Monitoring Accountable |
|----------|----------|-----------------|-------------------|------------------|---------------------|------------------------|
| IRIS-001 | PR-01    | Response Time   | End-to-end query response time | ≤ baseline + 20% | Continuous | Operations Team |
| IRIS-001 | PR-02    | Process Flow    | All expected process stages completed | 100% completion | Continuous | Operations Team |
| IRIS-001 | PR-03    | Resource Usage  | Token consumption per query | ≤ baseline + 15% | Daily | Operations Team |
| IRIS-001 | PR-04    | Error Rate      | Failed queries or process stages | ≤ 1% | Continuous | Operations Team |
| IRIS-001 | PR-05    | System Uptime   | Model availability for queries | ≥ 99.5% | Monthly | Operations Team |

### Remediation Process

In the event of threshold breaches, a defined escalation and remediation process will be followed. Automated alerts will notify the operations team of potential issues. An investigation using process monitoring tools will be conducted to identify root causes. Depending on severity, minor issues will be addressed by the operations team, significant issues will be escalated to the model owner, and critical issues will trigger immediate model suspension and emergency review. All incidents will be documented with resolution steps and preventative measures. A quarterly review of all incidents will be performed to identify patterns requiring model updates.

This comprehensive monitoring approach combines both performance evaluation (accuracy and quality of responses) with process monitoring (operational health) to ensure the IRIS model functions as expected over time. By leveraging the same quantitative methodology used in initial testing, we maintain consistency in evaluation criteria while adapting to evolving usage patterns and requirements.

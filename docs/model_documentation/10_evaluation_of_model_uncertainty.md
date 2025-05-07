# Section 10: Evaluation of Model Uncertainty

## 10.1 Uncertainty Assessment Approach

For the IRIS model, we have conducted a structured uncertainty assessment to quantify the level of uncertainty in model outputs and determine whether this uncertainty is acceptable given the model's intended use as a finance and accounting policy guidance tool.

Our assessment combines quantitative metrics from our testing results with qualitative analysis of uncertainty management mechanisms built into the system. This approach aligns with the requirements for models of medium materiality, focusing on quantifying uncertainty through empirical testing results, analyzing system behavior in edge cases and ambiguous scenarios, evaluating the system's ability to express appropriate confidence levels, and determining if the uncertainty is acceptable for the intended business use.

### 10.1.1 Uncertainty Measurement Methodology

We have employed multiple complementary approaches to measure uncertainty. These include using our **Accuracy Metrics** from quantitative testing results as inverse proxies for uncertainty, conducting **Error Analysis** by examining error patterns and failure modes in test cases, performing a **Confidence Signaling Assessment** to evaluate how the system communicates its confidence levels, and testing **Edge Case Performance** with ambiguous or out-of-scope queries.

### 10.1.2 Sources of Uncertainty

In the IRIS system, uncertainty can arise from several sources. **Database Selection Uncertainty** relates to the Router's ability to select the appropriate knowledge sources. **Information Retrieval Uncertainty** concerns the system's ability to identify relevant documents and passages. **Information Synthesis Uncertainty** pertains to the Summarizer's ability to accurately combine information from multiple sources. **Disambiguation Uncertainty** involves the Clarifier's ability to recognize and resolve ambiguous queries. Lastly, **Knowledge Boundary Uncertainty** is about the system's ability to recognize when information is unavailable or outside its scope.

## 10.2 Quantitative Uncertainty Assessment

Based on our comprehensive testing with both APG and non-APG databases, we have derived the following uncertainty measures:

### 10.2.1 Core Component Uncertainty

| Component | Metric | Result | Uncertainty Estimate | Interpretation |
|-----------|--------|--------|---------------------|----------------|
| Database Selection | Accuracy Rate | 99.4% | ±0.6% | Very low uncertainty in determining relevant knowledge sources |
| Document Retrieval | Accuracy Rate | 97.7% | ±2.3% | Low uncertainty in identifying relevant documents within databases |
| Answer Content | Accuracy Rate | 94.2% | ±5.8% | Low-moderate uncertainty in synthesizing accurate responses |
| Overall Performance | Combined Score | 89.6% | ±10.4% | Acceptable overall uncertainty for the intended use case |

### 10.2.2 Edge Case and Uncertainty Expression

| Uncertainty Dimension | Measurement | Result | Interpretation |
|----------------------|------------|--------|----------------|
| Knowledge Boundary Recognition | Appropriate refusal rate for out-of-scope queries | >95% | Low uncertainty in boundary recognition |
| Ambiguity Recognition | Rate of appropriate clarification requests | >90% | Low uncertainty in ambiguity detection |
| Confidence Expression | Alignment between expressed confidence and accuracy | >85% | Moderate uncertainty in confidence calibration |
| Source Conflict Resolution | Accuracy of prioritizing authoritative sources | >95% | Low uncertainty in conflict resolution |

### 10.2.3 Overall Uncertainty Assessment

Based on the quantitative measures above, the IRIS model demonstrates an overall uncertainty range of ±10.4%, with higher certainty in upstream components (database and document selection) and slightly lower certainty in response synthesis.

Given that the model is used as a research and guidance tool with explicit verification requirements rather than for direct decision-making, this level of uncertainty is assessed as **ACCEPTABLE** for the intended business purpose.

## 10.3 Uncertainty Management Mechanisms

The IRIS system implements several mechanisms to appropriately manage and communicate uncertainty.

### 10.3.1 Router Agent Uncertainty Management

The Router Agent manages uncertainty by explicitly routing finance-related queries to research rather than direct response. For ambiguous queries, the system follows a "when in doubt, research" approach. Additionally, a secondary safety layer exists in the Direct Response agent, which refuses to answer finance-related questions without research.

### 10.3.2 Clarifier Agent Uncertainty Recognition

The Clarifier Agent recognizes uncertainty by triggering specific clarification requests for ambiguous or underspecified queries. For standard selection choices, such as IFRS versus GAAP, the system defaults to IFRS while explicitly indicating this assumption. Query intention ambiguity is surfaced to the user rather than the system making potentially incorrect assumptions.

### 10.3.3 Response Synthesis Uncertainty Communication

During response synthesis, the system explicitly acknowledges contradictions between different information sources. Authoritative source hierarchies are clearly established, with IASB for standards and CAPM for internal policy. All responses include disclaimers about verification requirements and the need for professional judgment.

### 10.3.4 Knowledge Boundary Communication

The system communicates knowledge boundaries by clearly stating when questions fall outside available knowledge sources. Temporal limitations of information are acknowledged, especially for recently updated standards. Document metadata, including last updated dates, are incorporated in responses where relevant.

## 10.4 Acceptability of Uncertainty

The uncertainty level in the IRIS model is deemed acceptable based on several factors. The **Business Context** is crucial, as the model serves as a research assistant rather than an automated decision-maker, with all outputs subject to human verification. **Risk Mitigation** measures, such as clear disclaimers, source attribution, and verification statements, mitigate the risk of incorrect information being acted upon. The model's **Comparative Performance** achieves accuracy comparable to or exceeding manual reference processes while providing enhanced consistency. Furthermore, the model demonstrates **Balanced Tradeoffs** between coverage (breadth of knowledge) and accuracy (depth and correctness). Finally, **Continuous Monitoring** ensures any drift in performance is quickly identified.

### 10.4.1 Materiality Assessment

Given that the model is used internally by finance professionals who are required to verify information against primary sources, the uncertainty present in the model is assessed as having a **Low Impact**, as users understand the tool provides research assistance, not definitive answers. There is a **Low Likelihood of Harm** because clear source attributions allow verification of important information. The model has a **Non-Critical Application**, as it is not used for regulatory filing or external reporting. All users are made aware of **Transparent Limitations** through training and in-system disclaimers.

### 10.4.2 Conclusion on Uncertainty

Based on the quantitative uncertainty estimates and the model's intended use, we conclude that the overall uncertainty level of ±10.4% is ACCEPTABLE for the model's business purpose. The uncertainty is appropriately managed through built-in mechanisms and is transparently communicated to users. Ongoing monitoring will ensure uncertainty remains within acceptable bounds.

## 10.5 Ongoing Uncertainty Monitoring

The uncertainty profile of the system will be continuously monitored through our quarterly evaluation process. The 50-question evaluation set includes specifically designed edge cases to test boundary recognition. The same quantitative metrics (database selection, document selection, answer accuracy) will be calculated quarterly. Any trend indicating increasing uncertainty will trigger a detailed analysis and potential model adjustments. User feedback from the Maven interface provides real-world validation of appropriate confidence signaling.

By maintaining consistent evaluation metrics between the initial testing and ongoing monitoring, we will track any changes in the system's uncertainty over time, ensuring it remains within acceptable bounds for its intended use.

# python/iris/src/chat_model/model.py
"""
Model Initialization and Setup Module

This module serves as the main entry point for the IRIS application,
handling the full initialization process including logging setup,
SSL configuration, OAuth authentication, conversation processing,
and the full agent orchestration flow.

Functions:
    model: Main initialization function that sets up the necessary components
           and processes incoming conversations

Dependencies:
    - logging
    - SSL certificate setup
    - OAuth authentication
    - Conversation processing
    - Agent orchestration
"""

import logging

def model(conversation=None):
    """
    Initialize the model by setting up SSL certificates, OAuth authentication,
    processing the input conversation if provided, and orchestrating the agent workflow.
    
    This function:
    1. Configures centralized logging
    2. Configures SSL certificates for secure communication
    3. Obtains an OAuth token for API authentication
    4. Processes the input conversation if provided
    5. Orchestrates the full agent workflow for handling the query
    
    Args:
        conversation (dict, optional): Conversation in OpenAI format with a 'messages' key.
            If None, only the initial setup is performed.
    
    Returns:
        dict: Result containing:
            - cert_path: SSL certificate path
            - token: OAuth token
            - processed_conversation: Processed conversation (if input was provided)
            - response_content: Final response content (if conversation was provided)
    """
    # Import modules - using relative imports for better portability
    from ..initial_setup.logging_config import configure_logging
    from ..initial_setup.ssl.ssl import setup_ssl
    from ..initial_setup.oauth.oauth import setup_oauth
    from ..conversation_setup.conversation import process_conversation
    from ..agents.agent_router.router import get_routing_decision
    from ..agents.agent_direct_response.response_from_conversation import response_from_conversation
    from ..agents.agent_clarifier.clarifier import clarify_research_needs
    from ..agents.agent_planner.planner import create_query_plan
    from ..agents.agent_judge.judge import evaluate_research_progress
    from ..agents.database_subagents.database_router import route_database_query
    
    # Set up centralized logging
    logger = configure_logging()
    
    logger.info("Initializing model setup...")
    
    # Set up SSL certificates for secure communication
    cert_path = setup_ssl()
    
    # Obtain OAuth token
    token = setup_oauth()
    
    # Process conversation if provided
    processed_conversation = None
    response_content = None
    
    if conversation:
        logger.info("Processing input conversation...")
        processed_conversation = process_conversation(conversation)
        logger.info(f"Conversation processed: {len(processed_conversation['messages'])} messages")
        
        # Get routing decision
        logger.info("Getting routing decision...")
        routing_decision = get_routing_decision(processed_conversation, token)
        logger.info(f"Routing decision received: {routing_decision['function_name']}")
        
        # Handle response based on routing decision
        if routing_decision["function_name"] == "response_from_conversation":
            # Direct response without research
            logger.info("Using direct response path based on routing decision")
            
            # Return a generator that yields response chunks for streaming
            def stream_direct_response():
                # Set up metadata in the first yield
                yield {
                    "cert_path": cert_path,
                    "token": token,
                    "processed_conversation": processed_conversation,
                    "type": "direct_response",
                    "response_chunk": None  # Initial chunk with no content
                }
                
                # Stream the actual response chunks
                for chunk in response_from_conversation(
                    processed_conversation, 
                    token, 
                    routing_decision["thought"]
                ):
                    yield {
                        "type": "direct_response",
                        "response_chunk": chunk
                    }
            
            # Return the generator directly
            return stream_direct_response()
            
        elif routing_decision["function_name"] == "research_from_database":
            # Research path
            logger.info("Using research path based on routing decision")
            
            # Step 1: Clarify research needs
            logger.info("Clarifying research needs...")
            clarifier_decision = clarify_research_needs(processed_conversation, token)
            
            # If we need more context, return a generator that yields the context questions
            if clarifier_decision["action"] == "request_essential_context":
                logger.info("Essential context needed, returning context questions")
                
                def stream_context_questions():
                    # Initial metadata
                    yield {
                        "cert_path": cert_path,
                        "token": token,
                        "processed_conversation": processed_conversation,
                        "type": "context_questions",
                        "response_chunk": None  # Initial chunk with no content
                    }
                    
                    # Stream the questions one by one
                    questions = clarifier_decision["output"].strip().split('\n')
                    for question in questions:
                        if question.strip():
                            yield {
                                "type": "context_questions",
                                "response_chunk": question.strip() + "\n"
                            }
                
                return stream_context_questions()
            
            # Otherwise, proceed with research
            logger.info("Creating research statement, proceeding with research")
            research_statement = clarifier_decision["output"]
            is_continuation = clarifier_decision.get("is_continuation", False)
            
            # Create a streaming generator for the research path
            def stream_research_results():
                # Initial metadata yield
                yield {
                    "cert_path": cert_path,
                    "token": token,
                    "processed_conversation": processed_conversation,
                    "type": "research_results",
                    "response_chunk": None,  # Initial chunk with no content
                    "stage": "init"
                }
                
                # Step 2: Create query plan
                logger.info("Creating database query plan...")
                yield {
                    "type": "research_results",
                    "response_chunk": "Creating research query plan...\n",
                    "stage": "planning"
                }
                
                query_plan = create_query_plan(research_statement, token, is_continuation)
                logger.info(f"Query plan created with {len(query_plan['queries'])} queries")
                
                yield {
                    "type": "research_results",
                    "response_chunk": f"Research plan created with {len(query_plan['queries'])} queries.\n\n",
                    "stage": "planning_complete"
                }
                
                # We now use the router to handle all database queries
                
                # Step 3: Execute queries and evaluate progress
                completed_queries = []
                remaining_queries = query_plan["queries"].copy()
                
                # Stream the strategy
                yield {
                    "type": "research_results",
                    "response_chunk": f"# Research Strategy\n{query_plan['overall_strategy']}\n\n# Executing Queries\n\n",
                    "stage": "execution_start"
                }
                
                query_counter = 0
                while remaining_queries:
                    # Take the next query
                    current_query = remaining_queries.pop(0)
                    query_counter += 1
                    
                    logger.info(f"Executing query on {current_query['database']}: {current_query['query']}")
                    
                    # Stream query start notification
                    yield {
                        "type": "research_results",
                        "response_chunk": f"## Query {query_counter}: {current_query['database']}\n",
                        "stage": "query_start",
                        "query_number": query_counter,
                        "database": current_query['database']
                    }
                    
                    yield {
                        "type": "research_results",
                        "response_chunk": f"Search: {current_query['query']}\n\n",
                        "stage": "query_details"
                    }
                    
                    # Get database name from the query
                    db_name = current_query["database"]
                    
                    # Execute the query
                    try:
                        yield {
                            "type": "research_results",
                            "response_chunk": "Searching database...\n",
                            "stage": "query_executing"
                        }
                        
                        results = route_database_query(db_name, current_query["query"], token)
                        current_query["results"] = results
                        completed_queries.append(current_query)
                        logger.info(f"Query completed successfully")
                        
                        # Stream the results
                        yield {
                            "type": "research_results",
                            "response_chunk": f"{results}\n\n",
                            "stage": "query_results"
                        }
                        
                    except Exception as e:
                        logger.error(f"Error executing query: {str(e)}")
                        error_message = f"Error: {str(e)}"
                        current_query["results"] = error_message
                        completed_queries.append(current_query)
                        
                        yield {
                            "type": "research_results",
                            "response_chunk": f"{error_message}\n\n",
                            "stage": "query_error"
                        }
                    
                    # If there are remaining queries, check if we should continue
                    if remaining_queries:
                        logger.info("Evaluating whether to continue research...")
                        yield {
                            "type": "research_results",
                            "response_chunk": "Evaluating research progress...\n",
                            "stage": "evaluation"
                        }
                        
                        judgment = evaluate_research_progress(
                            research_statement, 
                            completed_queries, 
                            remaining_queries, 
                            token
                        )
                        
                        if judgment["action"] == "stop_research":
                            logger.info(f"Research stopped early: {judgment['reason']}")
                            yield {
                                "type": "research_results",
                                "response_chunk": f"Research complete. {judgment['reason']}\n\n",
                                "stage": "early_termination",
                                "reason": judgment['reason']
                            }
                            break
                        
                        logger.info("Continuing with next query")
                        yield {
                            "type": "research_results",
                            "response_chunk": "Continuing with next query...\n\n",
                            "stage": "continue_research"
                        }
                
                # If we stopped early, add info about unprocessed queries
                if remaining_queries:
                    yield {
                        "type": "research_results",
                        "response_chunk": "\n## Unprocessed Queries\n",
                        "stage": "unprocessed_queries_header"
                    }
                    
                    yield {
                        "type": "research_results",
                        "response_chunk": "The following queries were planned but not executed:\n\n",
                        "stage": "unprocessed_queries_intro"
                    }
                    
                    for i, query in enumerate(remaining_queries):
                        yield {
                            "type": "research_results",
                            "response_chunk": f"- {query['database']}: {query['query']}\n",
                            "stage": "unprocessed_query",
                            "query_number": i+1
                        }
                
                # Final completion message
                yield {
                    "type": "research_results",
                    "response_chunk": "\n# Research Summary\n\n",
                    "stage": "summary_header"
                }
                
                yield {
                    "type": "research_results",
                    "response_chunk": f"Completed {len(completed_queries)} queries across {len(set(q['database'] for q in completed_queries))} databases.\n",
                    "stage": "summary_stats"
                }
                
                yield {
                    "type": "research_results",
                    "response_chunk": "Research process complete.\n",
                    "stage": "complete"
                }
            
            # Return the streaming generator
            return stream_research_results()
        
        else:
            # Unknown function - return error generator
            logger.error(f"Unknown routing function: {routing_decision['function_name']}")
            
            def stream_error_response():
                # Initial metadata
                yield {
                    "cert_path": cert_path,
                    "token": token,
                    "processed_conversation": processed_conversation,
                    "type": "error",
                    "response_chunk": None
                }
                
                # Error message
                yield {
                    "type": "error",
                    "response_chunk": "Error: Unable to process query due to internal routing error."
                }
            
            return stream_error_response()
    
    # If no conversation was provided, just return the setup information
    logger.info("Model initialization complete")
    
    # Return the basic initialization information
    return {
        "cert_path": cert_path,
        "token": token,
        "type": "initialization_only"
    }
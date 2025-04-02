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

def model(
    conversation=None,
    html_callback=None
):
    """
    Main model function that processes conversations and yields streaming responses.
    
    This function matches the signature and behavior of the original chat model,
    yielding response chunks directly as strings rather than as dictionaries.
    
    Args:
        conversation (dict, optional): Conversation in OpenAI format with a 'messages' key.
        html_callback (callable, optional): Callback function for HTML rendering (not used)
            
    Returns:
        generator: A generator that yields response chunks as strings
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
    from ..agents.agent_judge.judge import evaluate_research_progress, generate_streaming_summary
    from ..agents.database_subagents.database_router import route_database_query
    
    try:
        # Set up centralized logging
        logger = configure_logging()
        
        logger.info("Initializing model setup...")
        
        # Set up SSL certificates for secure communication
        cert_path = setup_ssl()
        
        # Obtain OAuth token
        token = setup_oauth()
        
        # Process conversation if provided
        if conversation:
            logger.info("Processing input conversation...")
            processed_conversation = process_conversation(conversation)
            logger.info(f"Conversation processed: {len(processed_conversation['messages'])} messages")
            
            # Get routing decision
            logger.info("Getting routing decision...")
            routing_decision = get_routing_decision(processed_conversation, token)
            
            # Handle response based on routing decision
            if routing_decision["function_name"] == "response_from_conversation":
                # Direct response without research
                logger.info("Using direct response path based on routing decision")
                
                # Get the streaming response directly - each chunk is already a string
                for chunk in response_from_conversation(
                    processed_conversation, 
                    token
                ):
                    yield chunk
                    
            elif routing_decision["function_name"] == "research_from_database":
                # Research path
                logger.info("Using research path based on routing decision")
                
                # Step 1: Clarify research needs
                logger.info("Clarifying research needs...")
                clarifier_decision = clarify_research_needs(processed_conversation, token)
                
                # If we need more context, yield the context questions directly as strings
                if clarifier_decision["action"] == "request_essential_context":
                    logger.info("Essential context needed, returning context questions")
                    
                    # Stream the questions, preserving any existing numbering
                    questions = clarifier_decision["output"].strip()
                    questions_text = "Before proceeding with research, please clarify:\n\n"
                    questions_text += questions
                    
                    yield questions_text
                
                # Otherwise, proceed with research
                else:  # create_research_statement
                    logger.info("Creating research statement, proceeding with research")
                    research_statement = clarifier_decision["output"]
                    is_continuation = clarifier_decision.get("is_continuation", False)
                    
                    # Step 2: Create query plan
                    logger.info("Creating database query plan...")
                    query_plan = create_query_plan(research_statement, token, is_continuation)
                    logger.info(f"Query plan created with {len(query_plan['queries'])} queries")
                    
                    # Create a formatted markdown box with research plan using horizontal rules
                    research_plan_box = "---\n"
                    research_plan_box += "# 📋 Research Plan\n\n"
                    research_plan_box += f"## Research Statement\n{research_statement}\n\n"
                    research_plan_box += "## Database Queries\n"
                    
                    for j, query in enumerate(query_plan["queries"]):
                        db_name = query["database"]
                        research_plan_box += f"{j+1}. {db_name}: {query['query']}\n"
                    
                    research_plan_box += "---\n\n"
                    
                    # Yield the entire research plan box
                    yield research_plan_box
                    
                    # Prepare lists to track queries and results
                    completed_queries = []
                    query_results = []
                    remaining_queries = query_plan["queries"].copy()
                    
                    # Process queries one by one
                    i = 0
                    while i < len(query_plan["queries"]) and remaining_queries:
                        # Get the current query
                        current_query = query_plan["queries"][i]
                        
                        # Remove from remaining and add to completed
                        remaining_queries.remove(current_query)
                        completed_queries.append(current_query)
                        
                        # Get database name from the query
                        db_name = current_query["database"]
                        
                        # Yield query information with improved formatting
                        query_header = "---\n"
                        query_header += f"## 🔍 Query {i+1}: {db_name} - {current_query['query']}\n\n"
                        yield query_header
                        
                        # Execute the query
                        try:
                            # Execute database query and yield result directly
                            results = route_database_query(db_name, current_query["query"], token)
                            current_query["results"] = results
                            query_results.append(results)
                            
                            # Yield result directly with ending horizontal rule
                            yield f"{results}\n\n---\n\n"
                            
                        except Exception as e:
                            logger.error(f"Error executing query: {str(e)}")
                            error_message = f"Error: {str(e)}\n\n"
                            current_query["results"] = error_message
                            query_results.append(error_message)
                            
                            yield f"{error_message}\n---\n\n"
                        
                        logger.info(f"Completed database query {i+1}/{len(query_plan['queries'])}: {db_name}")
                        
                        # Only consult judge if there are more queries to process
                        if remaining_queries:
                            # Consult judge to decide whether to continue
                            judgment = evaluate_research_progress(
                                research_statement, 
                                completed_queries, 
                                remaining_queries, 
                                token
                            )
                            
                            # Determine whether to continue
                            continue_research = (judgment["action"] == "continue_research")
                            
                            if not continue_research:
                                # Generate a streaming summary when stopping early with improved formatting
                                yield "\n---\n## 📊 Research Summary\n"
                                
                                # Get streaming summary from judge agent
                                for summary_chunk in generate_streaming_summary(
                                    research_statement,
                                    completed_queries,
                                    token
                                ):
                                    yield summary_chunk
                                
                                yield "\n\n---\n\n"
                                
                                # If stopping, provide information about remaining queries
                                if remaining_queries:
                                    yield format_remaining_queries(remaining_queries)
                                break
                        
                        # Move to next query
                        i += 1
                    
                    # When naturally completing all queries, stream the final research summary
                    if not remaining_queries and completed_queries:
                        # Yield a header for the research summary with improved formatting
                        yield "\n---\n## 📊 Research Summary\n"
                        
                        # Get streaming summary from judge agent
                        for summary_chunk in generate_streaming_summary(
                            research_statement,
                            completed_queries,
                            token
                        ):
                            yield summary_chunk
                        
                        # Add a buffer after the summary with closing horizontal rule
                        yield "\n\n---\n\n"
                    
                    # Final completion message
                    yield f"\nCompleted {len(completed_queries)} database queries.\n"
                    logger.info("Completed research process")
            
            else:
                # Unknown function - yield error
                logger.error(f"Unknown routing function: {routing_decision['function_name']}")
                yield "Error: Unable to process query due to internal routing error."
        
        else:
            # If no conversation was provided, yield initialization message
            logger.info("Model initialization complete")
            yield "Model initialized successfully, but no conversation was provided."
            
    except Exception as e:
        yield f"Error processing request: {str(e)}"

def format_remaining_queries(remaining_queries):
    """Format remaining queries for display to the user."""
    if not remaining_queries:
        return "There are no remaining database queries."
    
    message = "## ⏸️ Remaining Queries\n\n"
    message += "The following database queries were not processed:\n\n"
    for i, query in enumerate(remaining_queries, 1):
        message += f"**{i}.** {query['database']}: {query['query']}\n"
    
    message += "\nPlease let me know if you would like to continue with these remaining database queries in a new search."
    return message
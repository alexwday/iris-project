# Changes needed for debug_notebook.ipynb

# 1. Update the stage_order to arrange the timeline properly
# Modified stage_order (router at top, summary at bottom)
stage_order = [
    'router',       # Router decision
    'direct_response', # Direct response path
    'clarifier',    # Clarify research needs
    'planner',      # Create query plan
    # Database queries will be placed between planner and summary
    'summary',      # Generate final summary
]

# 2. Update the get_display_stage function to clean up database labels
# Replace the existing get_display_stage function with this:
def get_display_stage(stage_name):
    if stage_name.startswith('db_query_'):
        parts = stage_name.split('_')
        if len(parts) > 2:
            # Extract the database name without 'internal' or 'external' prefix
            db_name = parts[2]
            # Remove 'internal_' or 'external_' prefix if present
            if db_name.startswith('internal_'):
                db_name = db_name[9:]  # Remove 'internal_'
            elif db_name.startswith('external_'):
                db_name = db_name[9:]  # Remove 'external_'
                
            query_idx = parts[3] if len(parts) > 3 else '1'
            return f"{db_name} (Query {query_idx})"  # Use cleaned database name
        else:
            return "DB: Unknown"
    else:
        return stage_display_names.get(stage_name, stage_name.replace('_', ' ').title())

# 3. When getting the display name for database rows, also implement the clean-up:
# When creating the db_colors dictionary, modify the code to:
db_colors = {}
for stage in df_timeline['stage']:
    if stage.startswith('db_query_'):
        parts = stage.split('_')
        if len(parts) > 2:
            db_name = parts[2]
            query_idx = parts[3] if len(parts) > 3 else '1'
            is_external = 'external' in db_name
            
            # Get the display name for this database
            row = df_timeline[df_timeline['stage'] == stage].iloc[0]
            db_display = row['display_stage']
            
            # Choose color based on internal/external
            if is_external:
                idx = hash(db_name) % len(external_cmap)
                color = mcolors.rgb2hex(external_cmap[idx])
            else:
                idx = hash(db_name) % len(internal_cmap)
                color = mcolors.rgb2hex(internal_cmap[idx])
            
            db_colors[db_display] = color

from typing import Optional, Literal
import requests
from datetime import datetime,timedelta
from constants import INGESTER_URL
from tavily import TavilyClient
from constants import URL, INGESTER_URL
import constants as c
import os
import json
import asyncio
import aiohttp
import structlog
from langchain.tools import tool
logger = structlog.get_logger()

@tool
async def get_incident_details_by_incident_number(
    incident_number: str, environment_type: str = "daas"
) -> dict:
    """
    Get incident details by incident number from the ingester API.
    Args:
        incident_number: The incident number to get details for
        environment_type: The environment type to get details for
    Returns:
        dict: The incident details
    Example:
        get_incident_details_by_incident_number(incident_number="INC2301202600003", environment_type="daas")    
    Note:
        Use this to retrieve the details of a specific incident.
    """
    url = f"{URL}/getIncidentDetails"
    headers = {
        "UserName": "rgoNEXoN",
        "Password": "ZvFiumvAJgdGVYc",
        "Content-Type": "application/json",
    }

    payload = {
        "clientName": "",
        "environmentType": environment_type,
        "engineerUserId": 4036,
        "allIncidentDetails": False,
        "pageNumber": 1,
        "pageSize": 100,
        "botAssigned": 0,
        "assignedTo": 0,
        "filter": [{"field": "incidentNumber", "value": incident_number}],
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url, headers=headers, json=payload, timeout=30
            ) as resp:
                resp.raise_for_status()
                resp = await resp.json()
                incident = resp.get("data", [{}])[0]
                del incident["ipAddress"]
                if incident.get('productType') == 'Horizon Cloud on Azure Titan':
                    productType = 'Horizon'
                else:
                    productType = incident.get('productType', 'N/A')
                return resp
            return {"error": "Failed to get incident details"}
        except aiohttp.ClientError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

@tool
async def count_all_incidents(
    tag: str,
) -> dict:
    """
    Get incident counts for all generated categories.
    
    Makes separate API calls for each category using the category filter parameter.
    
    Returns:
        dict: Counts for each category
            {
                "total": 1234,
                "by_category": {
                    "Application Management": 145,
                    "Hardware & Devices": 234,
                    "Email & Communication": 189,
                    ...
                }
            }
    """
    categories = [
        "Application Management",
        "Hardware & Devices",
        "Email & Communication",
        "Network & Performance",
        "Access & Security",
        "Installation & Configuration",
        "File & Shared Resources",
        "Server & Infrastructure",
        "Feedback",
        "Others"
    ]
    if tag == "horizon":
        url = f"{INGESTER_URL}/categoriser/search?tag=horizon"
    elif tag == "avd":
        url = f"{INGESTER_URL}/categoriser/search?tag=AVD"
    elif tag == "ws1":
        url = f"{INGESTER_URL}/categoriser/search?tag=ws1"
    elif tag == "citrix":
        url = f"{INGESTER_URL}/categoriser/search?tag=citrix"
    else:
        url = f"{INGESTER_URL}/categoriser/search"
    category_counts = {}
    total_count = 0
    #print(f"@@Tag: {tag}")
    #print(f"@@: {url}")
    # Query each category separately
    for category in categories:
        params = {
            "query":"",
            "generated_category": category,
            "limit": 100000
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            results = response.json()
            #print("Parrams",params)
            #print("Results",results)
            count = len(results) if isinstance(results, list) else 0
            category_counts[category] = count
            total_count += count
            # logger.info(f"Category '{category}' count: {count}")
            #print(f"Category '{category}' count: {count}")
        except requests.exceptions.RequestException as e:
            # logger.error(f"Failed to query category {category}", error=str(e))
            #print(f"Failed to query category {category} error {str(e)}")
            category_counts[category] = 0
    
    return {
        "total": total_count,
        "by_category": category_counts
    }

@tool
async def get_sop_for_issue(query: str) -> dict:
    """
    Perform a semantic search for incidents using the ChromaDB API.
 
    Args:
        query (str): The search query string for semantic search.
 
    Returns:
        dict: The JSON response from the API or an error dict.
    """
    #print("inside sop tool")
    sop_url = f"{INGESTER_URL}/sop/search"
    categoriser_url = f"{INGESTER_URL}/categoriser/search"
    stats_url = f"{INGESTER_URL}/categoriser/stats"

    # Calculate date range: last 3 months from current date
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    params = {
        "query": query,
        "limit":3,
    }
    response_data = {
        "sop_data": None,
        "historic_resolution_data": None,
        "web_data": None
    }
 
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(sop_url, params=params, timeout=30)
            response.raise_for_status()
            raw_data = await response.json()
            response_data["sop_data"] = raw_data
            
        # web_data = await search_web(websocket, query)
        # response_data["web_data"] = web_data
        # Filter and summarize the data to reduce token usage
        #print(f"@@@@@@@@@@@@@response_data: {response_data}")
        # #print(f"@@@@@@@@@@@@@raw_data: {raw_data}")
    except aiohttp.ClientError as e:
        logger.error(f"Error calling API: {e}")
        # return {"error": str(e)}
    except asyncio.TimeoutError:
        logger.error("Request timed out")
        # return {"error": "Request timed out"}
    return response_data


@tool
async def get_incidents_by_category(
    query: str,
    limit: int,
    category: Optional[str],
    sub_category: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    generated_category: Optional[str],
    tag: str
) -> dict:
    """
    Search the categoriser API for incidents by query.
    
    Available query parameters:
    - query: Search query string (e.g., "email", "login", "password")
    - limit: Number of results to return (default: 3)
    - category: Filter by generated category (optional)
    - sub_category: Filter by corrected sub-category (optional)
    - start_date: Filter from this date in YYYY-MM-DD format (optional)
    - end_date: Filter until this date in YYYY-MM-DD format (optional)
    
    Args:
        query (str): Search query string
        limit (int): Number of results to return (default: 3)
        category (Optional[str]): Filter by specific category
        sub_category (Optional[str]): Filter by specific sub-category
        start_date (Optional[str]): Filter from this date (format: YYYY-MM-DD)
        end_date (Optional[str]): Filter until this date (format: YYYY-MM-DD)
        generated_category (Optional[str]): Filter by generated category name
        tag (str): Tag value to filter incidents by horizon or other product names
    Returns:
        dict: Structured response containing:
            - category_name: The category name (from generated_category parameter)
            - total: Total number of incidents found
            - incidents: List of categorised incidents with details including:
                - requestId: Incident request ID
                - record_date_timestamp: Timestamp of the record
                - correctedSubCategory: Sub-category of the incident
                - createdDate: When incident was created
                - generatedCategory: AI-generated category
                - resolution: Resolution details
                - description: Incident description
            - by_priority: Dictionary with priority counts (defaults to empty dict if priority not available)
            - top_smes: List of top subject matter experts (engineers) for the category with percentages
    
    Example:
        get_incidents_by_category(query="email", generated_category="Access & Security", limit=3)
    """
    #print(f"inside get_incidents_by_category")
    #print(f"parameters: query: {query}, limit: {limit}, category: {category}, sub_category: {sub_category}, start_date: {start_date}, end_date: {end_date}, generated_category: {generated_category}, tag: {tag}")
    if tag == "horizon":
        url = f"{INGESTER_URL}/categoriser/search?tag=horizon"
    elif tag == "avd":
        url = f"{INGESTER_URL}/categoriser/search?tag=AVD"
    elif tag == "ws1":
        url = f"{INGESTER_URL}/categoriser/search?tag=ws1"
    elif tag == "citrix":
        url = f"{INGESTER_URL}/categoriser/search?tag=citrix"
    else:
        url = f"{INGESTER_URL}/categoriser/search"
    
    # Build params dict, only include non-None values
    params = {
        "query": query,
        "limit": limit
    }
    #print(f"@@Tag for specific category: {tag}")
    #print(f"@@URL for specific category: {url}")
    if category:
        params["category"] = category
    if generated_category:
        params["generated_category"] = generated_category
    if sub_category:
        params["sub_category"] = sub_category
    # Use provided date filters if available, otherwise don't apply date filters
    # This matches the behavior of categorized_incidents() which shows all incidents
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    # Only apply default 30-day filter if no dates are provided AND we want to limit results
    # For now, we match categorized_incidents() behavior by not applying default date filters
    # Uncomment the lines below if you want to apply a default 30-day filter:
    # if not start_date and not end_date:
    #     params["start_date"] = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    #     params["end_date"] = datetime.now().strftime("%Y-%m-%d")
    if "start_date" in params:
        ...
        #print("Start date", params["start_date"])
    if "end_date" in params:
        ...
        #print("End date", params["end_date"])
    try:
        #print("Params from get_incidents_by_category", params)
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        incidents = response.json()
        #print("Response from get_incidents_by_category", incidents)
        # Handle error response
        if isinstance(incidents, dict) and "error" in incidents:
            return incidents
        
        # Ensure incidents is a list
        if not isinstance(incidents, list):
            incidents = []
        
        # Calculate priority breakdown if priority field exists in incidents
        by_priority = {}
        if incidents and isinstance(incidents[0], dict):
            # Check if priority field exists
            if "priority" in incidents[0]:
                for incident in incidents:
                    priority = incident.get("priority", "Unknown")
                    by_priority[priority] = by_priority.get(priority, 0) + 1
            # If no priority field, set default empty dict
            # ResponseAgent will handle this gracefully
        
        # Calculate ageing analysis and subcategory status for charts
        ageing_counts = {"0-7": 0, "8-14": 0, "15-30": 0, "30+": 0}
        subcategory_status = {}  # {subcategory: {"resolved": 0, "pending": 0, "open": 0}}
        current_date = datetime.now()
        
        for incident in incidents:
            # Calculate ageing from created_at or created_at_timestamp
            # Try multiple field names to support different data formats
            created_date_value = (
                incident.get("created_at_timestamp") or 
                incident.get("created_at") or 
                incident.get("createdDate") or 
                incident.get("created_date")
            )
            days_old = 0  # Default to 0-7 days
            
            if created_date_value:
                try:
                    # Handle different date formats
                    if isinstance(created_date_value, (int, float)):
                        # It's a timestamp (Unix timestamp)
                        created_date = datetime.fromtimestamp(created_date_value)
                        days_old = (current_date - created_date).days
                    elif isinstance(created_date_value, str):
                        # It's a string - try to parse it
                        # ISO format: "2025-07-21T10:27:57.93Z" or "2025-11-20T15:55:10.22Z"
                        if "T" in created_date_value:
                            # ISO format with time
                            try:
                                # Remove microseconds and timezone for simpler parsing
                                date_str = created_date_value.split("T")[0]  # Get "YYYY-MM-DD"
                                if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                                    year, month, day = int(date_str[0:4]), int(date_str[5:7]), int(date_str[8:10])
                                    created_date = datetime(year, month, day)
                                    days_old = (current_date - created_date).days
                                else:
                                    # Try full ISO parsing
                                    created_date = datetime.fromisoformat(created_date_value.replace("Z", "+00:00").split(".")[0])
                                    days_old = (current_date - created_date.replace(tzinfo=None)).days
                            except (ValueError, AttributeError, IndexError):
                                # Fallback: try to extract date part
                                date_part = created_date_value[:10] if len(created_date_value) >= 10 else created_date_value
                                if len(date_part) == 10 and date_part[4] == '-' and date_part[7] == '-':
                                    year, month, day = int(date_part[0:4]), int(date_part[5:7]), int(date_part[8:10])
                                    created_date = datetime(year, month, day)
                                    days_old = (current_date - created_date).days
                        elif len(created_date_value) >= 10:
                            # Other string format: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
                            date_part = created_date_value[:10]
                            if len(date_part) == 10 and date_part[4] == '-' and date_part[7] == '-':
                                # Direct parsing without split/replace operations
                                year, month, day = int(date_part[0:4]), int(date_part[5:7]), int(date_part[8:10])
                                created_date = datetime(year, month, day)
                                days_old = (current_date - created_date).days
                            else:
                                # Try parsing the full string
                                try:
                                    created_date = datetime.strptime(created_date_value.split()[0], "%Y-%m-%d")
                                    days_old = (current_date - created_date).days
                                except (ValueError, IndexError):
                                    days_old = 0
                        else:
                            # String too short, assume recent
                            days_old = 0
                    else:
                        # Unknown type, assume recent
                        days_old = 0
                except (ValueError, AttributeError, TypeError, IndexError, OSError) as e:
                    # If date parsing fails, assume 0-7 days (recent)
                    #print(f"Warning: Could not parse date '{created_date_value}': {e}")
                    days_old = 0
            
            # Categorize by age
            if days_old <= 7:
                ageing_counts["0-7"] += 1
            elif days_old <= 14:
                ageing_counts["8-14"] += 1
            elif days_old <= 30:
                ageing_counts["15-30"] += 1
            else:
                ageing_counts["30+"] += 1
            
            # Calculate subcategory status
            # Try multiple field names for subcategory
            subcategory = (
                incident.get("correctedSubCategory") or 
                incident.get("corrected_sub_category") or 
                incident.get("subCategory") or
                incident.get("sub_category") or
                "Other"
            )
            if subcategory not in subcategory_status:
                subcategory_status[subcategory] = {"resolved": 0, "pending": 0, "open": 0}
            
            # Determine status: check stage field first (new format), then fallback to issueStatus
            # Note: Category incidents use 'issueStatus' field, regular incidents use 'stage' field
            stage = incident.get("stage", "") or incident.get("Stage", "")
            issue_status = incident.get("issueStatus", "") or incident.get("IssueStatus", "")
            resolution_note = incident.get("resolutionNote") or incident.get("resolution", "") or incident.get("Resolution", "")
            
            # Map stage values to status categories
            # Stage values: 'Closed', 'Verification', 'Resolution in Progress', etc.
            # IssueStatus values: 'Open', 'Pending', 'Resolved', etc.
            if stage:
                stage_lower = stage.lower().strip()
                # Check for resolved status - use keyword matching to catch variations
                resolved_keywords = ["closed", "resolved", "completed", "resolved - completed", "closed - verified", 
                                     "resolved - verified", "closed - resolved", "completed - verified", "Done"]
                # Check for pending/in-progress status
                pending_keywords = ["verification", "pending", "in progress", "resolution in progress", 
                                   "isolation", "on hold", "hold", "in queue", "assigned", "investigation",
                                   "work in progress", "wip"]
                
                # Check if stage contains any resolved keyword
                is_resolved = any(keyword in stage_lower for keyword in resolved_keywords)
                # Check if stage contains any pending keyword
                is_pending = any(keyword in stage_lower for keyword in pending_keywords)
                
                if is_resolved:
                    subcategory_status[subcategory]["resolved"] += 1
                elif is_pending:
                    subcategory_status[subcategory]["pending"] += 1
                else:
                    # If resolution note exists, consider it resolved
                    if resolution_note and resolution_note.strip():
                        subcategory_status[subcategory]["resolved"] += 1
                    else:
                        subcategory_status[subcategory]["open"] += 1
            elif issue_status:
                # Fallback to issueStatus if stage is not available (used by category incidents)
                status_lower = issue_status.lower().strip()
                # Check for resolved status
                if (status_lower == "done" or status_lower == "resolved" or "done" in status_lower or "resolved" in status_lower or "closed" in status_lower or "completed" in status_lower):
                    subcategory_status[subcategory]["resolved"] += 1
                # Check for pending status
                # elif status_lower == "pending" or "pending" in status_lower or "in progress" in status_lower or "verification" in status_lower:
                elif (status_lower == "pending" or status_lower == "on hold" or status_lower == "escalated" or status_lower == "waiting for customer" or status_lower == "in progress" or status_lower == "review with engineering" or "pending" in status_lower or "on hold" in status_lower or "escalated" in status_lower or "waiting" in status_lower or "in progress" in status_lower or "verification" in status_lower or"review with engineering" in status_lower):
                    subcategory_status[subcategory]["pending"] += 1
                # Check for open status - but also check if it might be pending based on other fields
                elif status_lower == "open" or "open" in status_lower:
                    # If resolution note exists, consider it resolved even if status is "open"
                    if resolution_note and resolution_note.strip():
                        subcategory_status[subcategory]["resolved"] += 1
                    else:
                        # Check if there are other indicators of pending status
                        # For category incidents, "Open" usually means truly open, not pending
                        subcategory_status[subcategory]["open"] += 1
                else:
                    # Unknown status, default to open
                    subcategory_status[subcategory]["open"] += 1
            else:
                # Fallback: check resolution note and other status fields
                status_details = incident.get("statusDetails") or incident.get("status", "") or incident.get("Status", "")
                
                if resolution_note and resolution_note.strip():
                    # Has resolution note, likely resolved
                    subcategory_status[subcategory]["resolved"] += 1
                elif status_details:
                    status_details_lower = status_details.lower().strip()
                    if status_details_lower == "resolved" or "resolved" in status_details_lower:
                        subcategory_status[subcategory]["resolved"] += 1
                    elif status_details_lower == "pending" or "pending" in status_details_lower:
                        subcategory_status[subcategory]["pending"] += 1
                    else:
                        subcategory_status[subcategory]["open"] += 1
                else:
                    # Default to open
                    subcategory_status[subcategory]["open"] += 1 
        # Get top 8 subcategories by total count
        subcategory_totals = {
            subcat: data["resolved"] + data["pending"] + data["open"]
            for subcat, data in subcategory_status.items()
        }
        top_subcategories = sorted(subcategory_status.items(), key=lambda x: subcategory_totals[x[0]], reverse=True)[:8]
        
        # Build chart data
        chart1_data = {
            "type": "bar",
            "data": {
                "labels": ["0-7 days", "8-14 days", "15-30 days", "30+ days"],
                "datasets": [{
                    "label": "Incidents",
                    "data": [ageing_counts["0-7"], ageing_counts["8-14"], ageing_counts["15-30"], ageing_counts["30+"]],
                    "backgroundColor": ["#3B82F6", "#60A5FA", "#93C5FD", "#DBEAFE"],
                    "borderWidth": 1,
                    "borderColor": "#ffffff"
                }]
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": "Incident Ageing Analysis",
                        "font": {"size": 18, "weight": "bold"}
                    },
                    "legend": {"display": False}
                },
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {
                            "display": True,
                            "text": "Number of Incidents (Count)"
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Age Range (Days)"
                        }
                    }
                }
            }
        }
        
        # Build chart2 data
        # Ensure we have at least empty arrays if no subcategories
        if top_subcategories:
            chart2_labels = [subcat for subcat, _ in top_subcategories]
            chart2_resolved = [subcategory_status[subcat]["resolved"] for subcat in chart2_labels]
            chart2_pending = [subcategory_status[subcat]["pending"] for subcat in chart2_labels]
            chart2_open = [subcategory_status[subcat]["open"] for subcat in chart2_labels]
        else:
            # No subcategories - use empty arrays
            chart2_labels = []
            chart2_resolved = []
            chart2_pending = []
            chart2_open = []
        
        chart2_data = {
            "type": "bar",
            "data": {
                "labels": chart2_labels,
                "datasets": [
                    {
                        "label": "Resolved",
                        "data": chart2_resolved,
                        "backgroundColor": "#10B981",
                        "borderWidth": 1,
                        "borderColor": "#ffffff"
                    },
                    {
                        "label": "Pending",
                        "data": chart2_pending,
                        "backgroundColor": "#F59E0B",
                        "borderWidth": 1,
                        "borderColor": "#ffffff"
                    },
                    {
                        "label": "Open",
                        "data": chart2_open,
                        "backgroundColor": "#EF4444",
                        "borderWidth": 1,
                        "borderColor": "#ffffff"
                    }
                ]
            },
            "options": {
                "indexAxis": "y",
                "responsive": True,
                "maintainAspectRatio": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": "Issue Status by Subcategory",
                        "font": {"size": 18, "weight": "bold"}
                    },
                    "legend": {
                        "display": True,
                        "position": "top"
                    }
                },
                "scales": {
                    "x": {
                        "beginAtZero": True,
                        "title": {
                            "display": True,
                            "text": "Number of Incidents (Count)"
                        }
                    },
                    "y": {
                        "title": {
                            "display": True,
                            "text": "Subcategory"
                        }
                    }
                }
            }
        }
        
        # Serialize charts to JSON string
        charts_json = json.dumps([chart1_data, chart2_data])
        
        # Validate the JSON is correct and can be parsed
        try:
            parsed_charts = json.loads(charts_json)
            if not isinstance(parsed_charts, list) or len(parsed_charts) != 2:
                #print(f"ERROR: Chart JSON validation failed - expected list of 2 charts, got {type(parsed_charts)}")
                # Return error instead of invalid JSON
                charts_json = json.dumps([chart1_data, chart2_data])  # Try again
                parsed_charts = json.loads(charts_json)
            
            # CRITICAL: Verify both charts have required structure and fix if needed
            charts_need_fix = False
            for i, chart in enumerate(parsed_charts):
                if not isinstance(chart, dict):
                    #print(f"ERROR: Chart {i} is not a dict - regenerating...")
                    charts_need_fix = True
                    break
                if "type" not in chart or "data" not in chart:
                    #print(f"ERROR: Chart {i} is missing required fields (type or data) - regenerating...")
                    charts_need_fix = True
                    break
                if "options" not in chart:
                    #print(f"ERROR: Chart {i} is missing 'options' field - fixing by regenerating...")
                    charts_need_fix = True
                    break
            
            # If any chart is malformed, regenerate from source data
            if charts_need_fix:
                #print(f"WARNING: Regenerating charts due to structural issues...")
                charts_json = json.dumps([chart1_data, chart2_data])
                parsed_charts = json.loads(charts_json)
            
            # CRITICAL: Ensure JSON is properly formatted and ends with closing bracket
            # Re-parse and re-serialize to ensure it's valid and complete
            charts_json = json.dumps(parsed_charts)
            # Double-check it ends with ']' and can be parsed
            if not charts_json.endswith(']'):
                #print(f"ERROR: Chart JSON does not end with ']' - fixing...")
                charts_json = json.dumps(parsed_charts)
            # Final validation parse - this will raise if invalid
            final_parsed = json.loads(charts_json)
            # Verify structure one more time
            if not isinstance(final_parsed, list) or len(final_parsed) != 2:
                raise ValueError("Final validation failed - not a list of 2 charts")
            for i, chart in enumerate(final_parsed):
                if "options" not in chart:
                    raise ValueError(f"Chart {i} missing 'options' field after final validation")
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            #print(f"ERROR: Generated chart JSON is invalid: {e} - regenerating from source...")
            # Regenerate from source data
            charts_json = json.dumps([chart1_data, chart2_data])
            # Final check
            if not charts_json.endswith(']'):
                #print(f"CRITICAL ERROR: Regenerated chart JSON still does not end with ']'")
                charts_json = json.dumps([chart1_data, chart2_data])
            # Verify the regenerated JSON is valid
            try:
                final_check = json.loads(charts_json)
                if len(final_check) != 2 or "options" not in final_check[0] or "options" not in final_check[1]:
                    print(f"CRITICAL ERROR: Regenerated JSON still has structural issues!")
            except Exception as e2:
                print(f"CRITICAL ERROR: Regenerated JSON cannot be parsed: {e2}")

        
        # Calculate summary statistics
        ageing_analysis = {
            "0-7": ageing_counts["0-7"],
            "8-14": ageing_counts["8-14"],
            "15-30": ageing_counts["15-30"],
            "30+": ageing_counts["30+"]
        }
        
        # CRITICAL: Final validation before returning - ensure chart_data is valid JSON
        # This prevents issues where the JSON might get corrupted during agent processing
        try:
            # Verify it can be parsed and is a list of 2 charts
            final_validation = json.loads(charts_json)
            if not isinstance(final_validation, list) or len(final_validation) != 2:
                #print(f"WARNING: Chart data validation failed before return - regenerating...")
                charts_json = json.dumps([chart1_data, chart2_data])
                final_validation = json.loads(charts_json)
            
            # CRITICAL: Verify both charts have "options" field
            for i, chart in enumerate(final_validation):
                if not isinstance(chart, dict):
                    raise ValueError(f"Chart {i} is not a dict")
                if "options" not in chart:
                    #print(f"CRITICAL: Chart {i} missing 'options' field before return - regenerating...")
                    charts_json = json.dumps([chart1_data, chart2_data])
                    final_validation = json.loads(charts_json)
                    break
                if "type" not in chart or "data" not in chart:
                    #print(f"CRITICAL: Chart {i} missing required fields before return - regenerating...")
                    charts_json = json.dumps([chart1_data, chart2_data])
                    final_validation = json.loads(charts_json)
                    break
            
            # Ensure it ends with ']' (array closing bracket)
            if not charts_json.endswith(']'):
                #print(f"WARNING: Chart data does not end with ']' - fixing...")
                charts_json = json.dumps([chart1_data, chart2_data])
            
            # Final parse to ensure it's valid
            final_check = json.loads(charts_json)
            # Verify both charts have options
            if len(final_check) != 2 or "options" not in final_check[0] or "options" not in final_check[1]:
                raise ValueError("Final check failed - charts missing options field")
        except (json.JSONDecodeError, ValueError, KeyError, Exception) as e:
            #print(f"ERROR: Chart data validation failed before return: {e} - regenerating...")
            charts_json = json.dumps([chart1_data, chart2_data])
            # Verify regenerated JSON
            try:
                verify = json.loads(charts_json)
                if len(verify) != 2 or "options" not in verify[0] or "options" not in verify[1]:
                    print(f"CRITICAL ERROR: Regenerated JSON still missing options field!")
            except Exception as e2:
                print(f"CRITICAL ERROR: Regenerated JSON cannot be parsed: {e2}")

        # Return structured response with pre-calculated chart data
        # NOTE: We don't include the full incidents list to reduce payload size
        # The agent only needs the summaries for the report
        engineer_percentages = {}
        for incident in incidents:
            # Check if top_engineers_for_category exists in the incident
            top_engineers = incident.get("top_engineers_for_category", [])
            if top_engineers and isinstance(top_engineers, list):
                for engineer_data in top_engineers:
                    if isinstance(engineer_data, dict):
                        engineer_name = engineer_data.get("engineer", "Unknown")
                        percentage = engineer_data.get("percentage", 0.0)
                        
                        # Aggregate percentages across all incidents
                        if engineer_name in engineer_percentages:
                            # Keep the max percentage seen for this engineer
                            engineer_percentages[engineer_name] = max(engineer_percentages[engineer_name], percentage)
                        else:
                            engineer_percentages[engineer_name] = percentage
        
        # Convert to list format and sort by percentage (descending)
        top_smes = [
            {"engineer": engineer, "percentage": percentage}
            for engineer, percentage in engineer_percentages.items()
        ]
        top_smes.sort(key=lambda x: x["percentage"], reverse=True)
        
        # Take top 5 SMEs
        top_smes = top_smes[:5]
        

        category_name = generated_category or category or "Unknown"
        rep = {
            "category_name": category_name,
            "total": len(incidents),
            "incidents_count": len(incidents),  # Just the count, not the full list
            "by_priority": by_priority,
            "ageing_analysis": ageing_analysis,
            "subcategory_status": subcategory_status,
            "chart_data": charts_json,  # Pre-calculated chart JSON string
            "top_smes": top_smes,  # Top subject matter experts for this category
            "is_empty": False  # Flag to indicate data exists
        }
        # Final verification before returning
        try:
            verify_charts = json.loads(charts_json)
            has_options = len(verify_charts) == 2 and "options" in verify_charts[0] and "options" in verify_charts[1]
            #print(f"Response from get_incidents_by_category: {category_name}, total: {len(incidents)}, chart_data length: {len(charts_json)}, ends with ']': {charts_json.endswith(']')}, has_options: {has_options}")
        except Exception as e:
            print(f"WARNING: Could not verify chart_data before return: {e}")
        #print(f"resp sent to agent {rep}")
        return rep
    except requests.exceptions.RequestException as e:
        #print("Error in get_incidents_by_category", e)
        return {"error": str(e)}


tavily_client = TavilyClient(api_key=c.config["TAVILY_API_KEY"])

@tool
def internet_search(
    query: str,
    max_results: int = 5,
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
    )
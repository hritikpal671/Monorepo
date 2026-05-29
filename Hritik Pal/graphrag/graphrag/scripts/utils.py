"""
Utility functions and example scripts for GraphRAG
"""

import pandas as pd
from datetime import datetime

from src.graphrag_app import GraphRAGApplication


def create_sample_csv(filename: str = "sample_data.csv"):
    """
    Create a sample CSV file for testing
    
    Args:
        filename: Name of the CSV file to create
    """
    data = {
        'ID': [1, 2, 3, 4, 5],
        'Name': ['Alice Johnson', 'Bob Smith', 'Carol White', 'David Brown', 'Emma Davis'],
        'Company': ['Tech Corp', 'Finance Inc', 'Tech Corp', 'Finance Inc', 'Media Ltd'],
        'Location': ['New York', 'Boston', 'San Francisco', 'New York', 'Los Angeles'],
        'Department': ['Engineering', 'Finance', 'Product', 'Analysis', 'Creative'],
        'Salary': [120000, 95000, 110000, 85000, 100000]
    }
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"[OK] Sample CSV created: {filename}")
    return filename


def quick_example():
    """Quick example to test the system"""
    print("=" * 60)
    print("GraphRAG Quick Example")
    print("=" * 60 + "\n")
    
    # Create sample data
    sample_file = create_sample_csv()
    
    # Initialize app
    print("\nInitializing GraphRAG...")
    app = GraphRAGApplication()
    
    # Ingest file
    print("\nIngesting CSV file...")
    app.ingest_file(sample_file)
    
    # Show data statistics
    print("\nData Statistics:")
    app.get_data_statistics()
    
    # Build graph
    print("\nBuilding knowledge graph...")
    app.build_graph()
    
    # Answer questions
    print("\nAnswering questions...\n")
    
    questions = [
        "Who works in Tech Corp?",
        "What is the average salary?",
        "Which locations have employees?"
    ]
    
    for question in questions:
        print(f"\nQ: {question}")
        result = app.answer_question(question)
    
    # Clean up
    app.close()
    
    print("\n[OK] Example completed!")


def batch_process_files(file_list):
    """
    Process multiple files and build graphs
    
    Args:
        file_list: List of file paths
    """
    print("=" * 60)
    print("Batch Processing Files")
    print("=" * 60 + "\n")
    
    app = GraphRAGApplication()
    results = {}
    
    for file_path in file_list:
        print(f"\nProcessing: {file_path}")
        try:
            app.ingest_file(file_path)
            app.build_graph(clear_existing=True)
            
            stats = app.graph_builder.get_graph_stats()
            results[file_path] = {
                'status': 'success',
                'nodes': stats['total_nodes'],
                'relationships': stats['total_relationships']
            }
            print(f"[OK] Success - Nodes: {stats['total_nodes']}, Relationships: {stats['total_relationships']}")
        except Exception as e:
            results[file_path] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"[ERROR] Error: {str(e)}")
    
    app.close()
    
    # Print summary
    print("\n" + "=" * 60)
    print("Processing Summary")
    print("=" * 60)
    for file_path, result in results.items():
        status = result['status'].upper()
        print(f"{file_path}: {status}")
        if status == 'SUCCESS':
            print(f"  Nodes: {result['nodes']}, Relationships: {result['relationships']}")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")


def interactive_qa():
    """Interactive question answering loop"""
    print("=" * 60)
    print("Interactive Question Answering")
    print("=" * 60 + "\n")
    
    # Initialize
    app = GraphRAGApplication()
    
    # Get file to ingest
    file_path = input("Enter path to CSV/Excel file: ").strip()
    
    try:
        app.ingest_file(file_path)
        app.build_graph()
        
        print("\n[OK] Graph built successfully!")
        print("Type 'quit' to exit, 'stats' for statistics, 'summary' for graph summary\n")
        
        while True:
            question = input("Q: ").strip()
            
            if question.lower() == 'quit':
                break
            elif question.lower() == 'stats':
                app.get_data_statistics()
            elif question.lower() == 'summary':
                app.get_graph_summary()
            elif question:
                result = app.answer_question(question)
            else:
                print("Please enter a valid question")
    
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
    
    finally:
        app.close()


def generate_report(file_path: str, output_file: str = "report.txt"):
    """
    Generate a comprehensive report about the data
    
    Args:
        file_path: Path to the data file
        output_file: Path to save the report
    """
    print(f"Generating report from {file_path}...")
    
    app = GraphRAGApplication()
    app.ingest_file(file_path)
    app.build_graph()
    
    # Gather information
    stats = app.get_data_statistics()
    graph_stats = app.graph_builder.get_graph_stats()
    summary = app.query_engine.get_graph_summary()
    
    # Generate report
    report = f"""
GraphRAG Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Source File: {file_path}

DATA STATISTICS
===============
Total Rows: {stats['total_rows']}
Total Columns: {stats['total_columns']}
Columns: {', '.join(stats['columns'])}

Missing Values:
{chr(10).join([f"  {col}: {count}" for col, count in stats['missing_values'].items()])}

GRAPH STATISTICS
================
Total Nodes: {graph_stats['total_nodes']}
Total Relationships: {graph_stats['total_relationships']}

AI INSIGHTS
===========
{summary}
"""
    
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"[OK] Report saved to {output_file}")
    app.close()
    
    return report


def test_connection():
    """Test Neo4j and Gemini connections"""
    print("=" * 60)
    print("Testing Connections")
    print("=" * 60 + "\n")
    
    try:
        print("Testing Neo4j connection...")
        app = GraphRAGApplication()
        
        # Test Neo4j
        if app.graph_builder:
            stats = app.graph_builder.get_graph_stats()
            print(f"[OK] Neo4j connected successfully")
            print(f"  Current graph has {stats['total_nodes']} nodes")
        
        # Test Gemini
        if app.llm:
            test_response = app.llm.generate_text("Say 'Gemini API is working'")
            print(f"[OK] Gemini API connected successfully")
            print(f"  Response: {test_response}")
        
        app.close()
        print("\n[OK] All connections working!")
        
    except Exception as e:
        print(f"\n[ERROR] Connection test failed: {str(e)}")


def main():
    """Main menu for utilities"""
    print("""
+================================================================+
|              GraphRAG Utility Functions                        |
+================================================================+
    """)
    
    print("""
1. Quick Example
2. Batch Process Files
3. Interactive Q&A
4. Generate Report
5. Test Connection
6. Create Sample CSV
7. Exit
    """)
    
    choice = input("Enter your choice (1-7): ").strip()
    
    if choice == '1':
        quick_example()
    elif choice == '2':
        file_list = []
        print("Enter file paths (empty line to finish):")
        while True:
            file_path = input("File path: ").strip()
            if not file_path:
                break
            file_list.append(file_path)
        if file_list:
            batch_process_files(file_list)
    elif choice == '3':
        interactive_qa()
    elif choice == '4':
        file_path = input("Enter file path: ").strip()
        output_file = input("Enter output file name (default: report.txt): ").strip() or "report.txt"
        generate_report(file_path, output_file)
    elif choice == '5':
        test_connection()
    elif choice == '6':
        filename = input("Enter filename (default: sample_data.csv): ").strip() or "sample_data.csv"
        create_sample_csv(filename)
    elif choice == '7':
        print("Goodbye!")
    else:
        print("[ERROR] Invalid choice")


if __name__ == "__main__":
    main()

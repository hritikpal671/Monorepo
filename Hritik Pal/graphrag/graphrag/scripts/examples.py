"""
GraphRAG Examples - Demonstrates various use cases
Run this file to see examples: python examples.py
"""

import pandas as pd
import os

from src.graphrag_app import GraphRAGApplication


def example_1_basic_usage():
    """Example 1: Basic usage - Load file, build graph, answer question"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Usage")
    print("="*70)
    
    # Create sample data
    print("\n1. Creating sample data...")
    data = {
        'ID': [1, 2, 3, 4, 5],
        'Name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'Department': ['Engineering', 'Sales', 'Engineering', 'Marketing', 'Sales'],
        'Location': ['NYC', 'LA', 'NYC', 'Chicago', 'LA'],
        'Salary': [100000, 80000, 120000, 90000, 85000]
    }
    df = pd.DataFrame(data)
    df.to_csv('example1.csv', index=False)
    print("   [OK] Sample data created")
    
    # Initialize and process
    print("\n2. Initializing GraphRAG...")
    app = GraphRAGApplication()
    
    print("\n3. Ingesting file...")
    app.ingest_file('example1.csv')
    
    print("\n4. Building knowledge graph...")
    app.build_graph()
    
    print("\n5. Answering questions...")
    questions = [
        "How many employees are in Engineering?",
        "What's the average salary?",
        "Which locations have employees?"
    ]
    
    for question in questions:
        print(f"\n   Q: {question}")
        result = app.answer_question(question)
        print(f"   A: {result['answer'][:200]}...")
    
    app.close()
    print("\n[OK] Example 1 completed!")


def example_2_data_exploration():
    """Example 2: Explore and understand data"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Data Exploration")
    print("="*70)
    
    # Create richer sample data
    print("\n1. Creating sample data with relationships...")
    data = {
        'EmployeeID': list(range(1, 11)),
        'Name': ['Alice J.', 'Bob S.', 'Charlie B.', 'Diana P.', 'Eve W.',
                'Frank M.', 'Grace L.', 'Henry K.', 'Iris D.', 'Jack R.'],
        'Manager': ['None', 'Alice J.', 'Alice J.', 'Bob S.', 'Bob S.',
                   'Charlie B.', 'Charlie B.', 'Diana P.', 'Diana P.', 'Eve W.'],
        'Department': ['Engineering', 'Engineering', 'Engineering', 'Sales', 'Sales',
                      'Engineering', 'Engineering', 'Marketing', 'Marketing', 'Sales'],
        'Salary': [150000, 120000, 110000, 100000, 95000,
                  130000, 115000, 105000, 98000, 92000],
        'Location': ['NYC', 'NYC', 'NYC', 'LA', 'LA',
                    'Chicago', 'Chicago', 'Boston', 'Boston', 'LA']
    }
    df = pd.DataFrame(data)
    df.to_csv('example2.csv', index=False)
    print("   [OK] Sample data created")
    
    # Initialize
    app = GraphRAGApplication()
    app.ingest_file('example2.csv')
    
    # Get statistics
    print("\n2. Data Statistics:")
    stats = app.get_data_statistics()
    
    # Build graph
    print("\n3. Building knowledge graph...")
    app.build_graph()
    
    # Get graph summary
    print("\n4. Graph Summary:")
    summary = app.query_engine.get_graph_summary()
    
    app.close()
    print("\n[OK] Example 2 completed!")


def example_3_multiple_questions():
    """Example 3: Answer multiple questions at once"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Multiple Questions")
    print("="*70)
    
    # Create sample data
    print("\n1. Creating sample data...")
    data = {
        'Product': ['Laptop', 'Phone', 'Tablet', 'Monitor', 'Keyboard',
                   'Mouse', 'USB Cable', 'Screen Protector', 'Case', 'Charger'],
        'Category': ['Computers', 'Electronics', 'Electronics', 'Computers', 'Accessories',
                    'Accessories', 'Accessories', 'Accessories', 'Accessories', 'Accessories'],
        'Price': [1200, 800, 500, 300, 100, 50, 15, 10, 20, 40],
        'Stock': [15, 30, 25, 40, 100, 150, 200, 500, 300, 200],
        'Supplier': ['TechCorp', 'ElectroWorld', 'ElectroWorld', 'TechCorp', 'AccessoryPro',
                    'AccessoryPro', 'AccessoryPro', 'SmallGoods', 'SmallGoods', 'ChargeCo']
    }
    df = pd.DataFrame(data)
    df.to_csv('example3.csv', index=False)
    print("   [OK] Sample data created")
    
    # Initialize
    print("\n2. Initializing GraphRAG...")
    app = GraphRAGApplication()
    app.ingest_file('example3.csv')
    app.build_graph()
    
    # Ask multiple questions
    print("\n3. Answering multiple questions...")
    questions = [
        "What products are in stock?",
        "Which suppliers provide the most products?",
        "What's the price range of products?",
        "Which categories have the most items?"
    ]
    
    results = app.answer_multiple_questions(questions)
    
    print("\n4. Results Summary:")
    for i, result in enumerate(results, 1):
        print(f"\n   Question {i}: {result['question']}")
        print(f"   Confidence: {result['confidence']:.2%}")
    
    app.close()
    print("\n[OK] Example 3 completed!")


def example_4_entity_exploration():
    """Example 4: Explore entity relationships"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Entity Exploration")
    print("="*70)
    
    # Create sample data with clear entities
    print("\n1. Creating sample data...")
    data = {
        'Company': ['TechCorp', 'TechCorp', 'FinanceInc', 'FinanceInc', 'MediaLtd',
                   'TechCorp', 'FinanceInc', 'MediaLtd', 'TechCorp', 'MediaLtd'],
        'Employee': ['John', 'Sarah', 'Mike', 'Lisa', 'Tom',
                    'Emma', 'David', 'Anna', 'Peter', 'Chris'],
        'Location': ['NYC', 'NYC', 'Boston', 'Boston', 'LA',
                    'San Francisco', 'Boston', 'LA', 'NYC', 'LA'],
        'Role': ['Manager', 'Engineer', 'Analyst', 'Analyst', 'Creative',
                'Engineer', 'Manager', 'Creative', 'Manager', 'Creative'],
        'Salary': [120000, 100000, 95000, 92000, 85000,
                  105000, 110000, 90000, 125000, 88000]
    }
    df = pd.DataFrame(data)
    df.to_csv('example4.csv', index=False)
    print("   [OK] Sample data created")
    
    # Initialize
    print("\n2. Initializing GraphRAG...")
    app = GraphRAGApplication()
    app.ingest_file('example4.csv')
    app.build_graph()
    
    # Explore entities
    print("\n3. Exploring entities...")
    entities_to_explore = ['TechCorp', 'John', 'NYC']
    
    for entity in entities_to_explore:
        print(f"\n   Exploring: {entity}")
        result = app.explore_entity(entity, depth=1)
        print(f"   Found {result['count']} relationships")
    
    app.close()
    print("\n[OK] Example 4 completed!")


def example_5_data_analysis_workflow():
    """Example 5: Complete data analysis workflow"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Complete Data Analysis Workflow")
    print("="*70)
    
    # Create comprehensive sample data
    print("\n1. Creating comprehensive sample data...")
    data = {
        'Year': [2020, 2020, 2021, 2021, 2022, 2022, 2023, 2023, 2024, 2024],
        'Region': ['North', 'South', 'North', 'South', 'North', 'South', 'North', 'South', 'East', 'West'],
        'Product': ['Widget', 'Gadget', 'Widget', 'Gadget', 'Widget', 'Gadget', 'Widget', 'Gadget', 'Widget', 'Gadget'],
        'Revenue': [100000, 120000, 150000, 140000, 200000, 160000, 250000, 200000, 280000, 220000],
        'Units': [1000, 1200, 1500, 1400, 2000, 1600, 2500, 2000, 2800, 2200],
        'Growth': [5, 8, 50, 17, 33, 14, 25, 25, 12, 10]
    }
    df = pd.DataFrame(data)
    df.to_csv('example5.csv', index=False)
    print("   [OK] Sample data created")
    
    # Workflow steps
    print("\n2. Step 1: Load and inspect data...")
    app = GraphRAGApplication()
    app.ingest_file('example5.csv')
    stats = app.get_data_statistics()
    
    print("\n3. Step 2: Build knowledge graph...")
    app.build_graph()
    
    print("\n4. Step 3: Analyze trends...")
    analysis_questions = [
        "What's the revenue trend over years?",
        "Which region has better performance?",
        "What's the growth pattern?",
        "How do Widget and Gadget compare?"
    ]
    
    for question in analysis_questions:
        result = app.answer_question(question)
        print(f"\n   Q: {question}")
        print(f"   A: {result['answer'][:150]}...")
    
    print("\n5. Step 4: Summary and insights...")
    summary = app.query_engine.get_graph_summary()
    
    app.close()
    print("\n[OK] Example 5 completed!")


def main():
    """Main menu for examples"""
    print("""
+================================================================+
|              GraphRAG Examples                                 |
+================================================================+
    """)
    
    print("""
Available Examples:
1. Basic Usage - Load file, build graph, answer question
2. Data Exploration - Understand your data structure
3. Multiple Questions - Answer several questions at once
4. Entity Exploration - Explore entity relationships
5. Complete Workflow - Full data analysis workflow
6. Run All Examples
7. Exit
    """)
    
    choice = input("Enter your choice (1-7): ").strip()
    
    try:
        if choice == '1':
            example_1_basic_usage()
        elif choice == '2':
            example_2_data_exploration()
        elif choice == '3':
            example_3_multiple_questions()
        elif choice == '4':
            example_4_entity_exploration()
        elif choice == '5':
            example_5_data_analysis_workflow()
        elif choice == '6':
            example_1_basic_usage()
            example_2_data_exploration()
            example_3_multiple_questions()
            example_4_entity_exploration()
            example_5_data_analysis_workflow()
            print("\n" + "="*70)
            print("[OK] All examples completed!")
            print("="*70)
        elif choice == '7':
            print("Goodbye!")
        else:
            print("[ERROR] Invalid choice")
    
    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        print("Please check your configuration and try again.")
    
    finally:
        # Cleanup example files
        for file in ['example1.csv', 'example2.csv', 'example3.csv', 'example4.csv', 'example5.csv']:
            if os.path.exists(file):
                os.remove(file)


if __name__ == "__main__":
    main()

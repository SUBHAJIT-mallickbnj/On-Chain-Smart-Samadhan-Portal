import os
import pandas as pd
import json

def create_sample_data():
    """Create sample data files for development"""
    
    # Create department contacts
    dept_contacts = pd.DataFrame({
        'Department': ['Water Supply', 'Electricity', 'Roads', 'Sanitation', 'General'],
        'Phone': ['+1234567890', '+1234567891', '+1234567892', '+1234567893', '+1234567894'],
        'Email': ['water@city.gov', 'power@city.gov', 'roads@city.gov', 'sanitation@city.gov', 'general@city.gov']
    })
    dept_contacts.to_csv("department_contacts.csv", index=False)
    print("✅ Created department_contacts.csv")
    
    # Create sample training data
    training_data = pd.DataFrame({
        'complaint_text': [
            'Water supply has been disrupted for 3 days',
            'Street lights are not working',
            'Road is full of potholes',
            'Garbage not collected for a week',
            'Need information about city services'
        ],
        'product': ['Water Supply', 'Electricity', 'Roads', 'Sanitation', 'General']
    })
    training_data.to_csv("consumer_complaints.csv", index=False)
    print("✅ Created consumer_complaints.csv")
    
    # Create .env template
    env_template = """# Blockchain Configuration
BLOCKCHAIN_NETWORK=http://127.0.0.1:8545
CONTRACT_ADDRESS=
PRIVATE_KEY=your_private_key_here
FLASK_SECRET_KEY=your-super-secret-key-here

# Application Settings
FLASK_ENV=development
FLASK_DEBUG=True
AUTO_DEPLOY=false
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_template)
        print("✅ Created .env template")
    else:
        print("ℹ️ .env file already exists")
    
    # Create directories
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('contracts', exist_ok=True)
    print("✅ Created necessary directories")

if __name__ == "__main__":
    create_sample_data()
    print("\n🎉 Setup complete! Now run:")
    print("1. pip install -r requirements.txt")
    print("2. Start Ganache: ganache-cli --accounts 10")
    print("3. Update .env with your private key")
    print("4. Deploy contract: cd contracts && python deploy.py")
    print("5. Run app: python app.py")
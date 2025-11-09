// Test script to check backend connection
const testBackendConnection = async () => {
  try {
    console.log('Testing connection to backend...');
    const response = await fetch('http://127.0.0.1:8000/api/v1/hypotheses');
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('✅ Backend connection successful!');
    console.log('Response data:', data);
    return true;
  } catch (error) {
    console.error('❌ Failed to connect to backend:', error.message);
    console.log('Please make sure:');
    console.log('1. The backend server is running');
    console.log('2. CORS is properly configured in the backend');
    console.log('3. The backend URL is correct');
    return false;
  }
};

// Run the test
testBackendConnection();

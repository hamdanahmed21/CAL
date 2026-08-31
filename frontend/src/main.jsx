
import React from 'react'
import ReactDOM from 'react-dom/client'
import Chatbot from './components/Chatbot/Chatbot'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      backgroundColor: '#f9fafb'
    }}>
      <Chatbot />
    </div>
  </React.StrictMode>
)
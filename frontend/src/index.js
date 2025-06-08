import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom'; // Import the router
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* Wrap your App component with the router */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
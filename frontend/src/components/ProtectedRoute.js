import React from 'react';
import { Navigate } from 'react-router-dom';

// This component is a wrapper around our routes
const ProtectedRoute = ({ children }) => {
    // Check for the token in local storage
    const token = localStorage.getItem('token');

    if (!token) {
        // If no token is found, redirect to the login page
        return <Navigate to="/login" />;
    }

    // If a token exists, render the component that was passed as a child
    return children;
};

export default ProtectedRoute;
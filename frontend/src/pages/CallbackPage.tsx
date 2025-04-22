import { useAuth0 } from '@auth0/auth0-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import authConfig from '../config/auth';

export const CallbackPage = () => {
  const { isLoading, isAuthenticated, error } = useAuth0();
  const navigate = useNavigate();

  // Log any errors for debugging
  useEffect(() => {
    if (error) {
      console.error('Auth0 error:', error);
      console.log('Auth0 Configuration:', {
        domain: authConfig.auth0.domain,
        clientId: authConfig.auth0.clientId.substring(0, 5) + '...',
        audience: authConfig.auth0.audience,
        callbackUrl: window.location.origin + '/callback'
      });
    }
  }, [error]);

  // Redirect after successful authentication
  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        navigate('/');
      } else if (error) {
        // If there's an error, go back to login
        navigate('/login');
      }
    }
  }, [isLoading, isAuthenticated, error, navigate]);

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center">
      {error ? (
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-500 mb-3">Authentication Error</h2>
          <p className="text-gray-600">{error.message || 'An error occurred during authentication'}</p>
          <button
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            onClick={() => navigate('/login')}
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-gray-500">Processing authentication...</p>
        </>
      )}
    </div>
  );
};

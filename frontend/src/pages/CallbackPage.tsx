import { useAuth0 } from '@auth0/auth0-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

export const CallbackPage = () => {
  const { isLoading: auth0Loading, isAuthenticated, error, user } = useAuth0();
  const { getToken, isLoading: authContextLoading } = useAuth();
  const navigate = useNavigate();
  const [userSynced, setUserSynced] = useState<boolean>(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Combine both loading states
  const isLoading = auth0Loading || authContextLoading;

  // Create or update user in backend when authenticated
  useEffect(() => {
    const syncUser = async () => {
      if (isAuthenticated && user && !userSynced && !isLoading) {
        try {
          // Token is now managed by auth context
          const token = await getToken();

          if (!token) {
            console.error("No token available for API call");
            setSyncError("Authentication token not available");
            return;
          }

          // Extract relevant user data from Auth0 user object
          const userData = {
            email: user.email,
            name: user.name,
            picture: user.picture,
            auth0_id: user.sub,
            email_verified: user.email_verified,
            // Add any other fields you want to store
          };

          // Call backend API to create or update user
          const response = await apiClient.post('/users/create_or_update', userData);

          if (response.ok) {
            console.log("✅ User created/updated in backend");
            setUserSynced(true);
          } else {
            const errorText = await response.text();
            console.error("❌ Failed to create/update user:", errorText);
            setSyncError(`Failed to sync user data: ${response.status}`);
          }
        } catch (err) {
          console.error("❌ Error syncing user with backend:", err);
          setSyncError(err instanceof Error ? err.message : "Unknown error syncing user");
        }
      }
    };

    syncUser();
  }, [isAuthenticated, user, userSynced, isLoading, getToken]);

  // Handle navigation
  const goHome = () => navigate('/');
  const goLogin = () => navigate('/login');

  // Show appropriate UI based on state
  if (isLoading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-4">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <div className="text-center max-w-md">
          <h2 className="text-xl font-semibold text-red-500 mb-3">Authentication Error</h2>
          <p className="text-gray-600 mb-6">{error.message}</p>
          <Button onClick={goLogin}>Try Again</Button>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center">
        <div className="text-center max-w-md">
          <h2 className="text-xl font-semibold text-green-500 mb-3">Login Successful!</h2>
          <p className="text-gray-600 mb-6">
            Your authentication has been completed successfully.
          </p>
          {syncError && (
            <p className="text-red-500 mb-4">
              {syncError}
            </p>
          )}
          {userSynced && (
            <p className="text-green-500 mb-4">
              User profile synchronized with backend.
            </p>
          )}
          <Button onClick={goHome}>Continue to App</Button>
        </div>

        {/* Small debug indicator */}
        <div className="fixed bottom-4 left-4 text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded">
          Auth: {isAuthenticated ? "✅" : "❌"}
          {isAuthenticated && <span className="ml-2">User: {userSynced ? "✅" : "❌"}</span>}
        </div>
      </div>
    );
  }

  // Not authenticated
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold text-yellow-500 mb-3">Authentication Incomplete</h2>
        <p className="text-gray-600 mb-6">
          We couldn't complete your login. This might be due to missing permissions or a configuration issue.
        </p>
        <Button onClick={goLogin}>Back to Login</Button>
      </div>
    </div>
  );
};

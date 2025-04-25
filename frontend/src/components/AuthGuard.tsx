import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { Loader2 } from 'lucide-react';
import authConfig from '@/config/auth';
import { apiClient } from '@/lib/api';

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard = ({ children }: AuthGuardProps) => {
  const { isAuthenticated, isLoading, login, user, isReady } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Only redirect if auth is enabled, not loading, and not authenticated
    if (authConfig.authEnabled && !isLoading && !isAuthenticated) {
      navigate('/login', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && isReady()) {
      login();
    }
  }, [isLoading, isAuthenticated, login, isReady]);

  // Register user with backend after successful authentication
  useEffect(() => {
    const registerUser = async () => {
      if (isAuthenticated && user?.email && isReady()) {
        try {
          console.log("Registering authenticated user with backend", user?.email);
          const response = await apiClient.post("/users/create_or_update", {
            email: user.email,
            full_name: user.name || "User"
          });

          if (!response.ok) {
            console.error("Failed to register user with backend", await response.text());
          } else {
            console.log("User successfully registered with backend");
          }
        } catch (error) {
          console.error("Error registering user with backend:", error);
        }
      }
    };

    registerUser();
  }, [isAuthenticated, user, isReady]);

  // If auth is disabled, just render children
  if (!authConfig.authEnabled) {
    return <>{children}</>;
  }

  // Show loading spinner while checking auth status
  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // If authenticated, render children
  return isAuthenticated ? <>{children}</> : null;
};

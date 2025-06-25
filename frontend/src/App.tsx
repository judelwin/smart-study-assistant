import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ClassProvider } from './context/ClassContext';
import { DocumentRefreshProvider } from './context/DocumentRefreshContext';
import ClassSelector from './components/ClassSelector';
import ProtectedRoute from './components/ProtectedRoute';
import Upload from './pages/Upload';
import Chat from './pages/Chat';
import { UserProvider, useUserContext } from './context/UserContext';
import Login from './pages/Login';
import Register from './pages/Register';

function Navigation() {
  const { user, logout } = useUserContext();

  return (
    <header className="bg-white shadow-sm border-b z-10">
      <div className="px-4 sm:px-6 lg:px-8 w-full">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-gray-800">ClassGPT</h1>
          </div>
          <div className="flex items-center space-x-8">
            <Link
              to="/upload"
              className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition duration-200"
            >
              Upload
            </Link>
            <Link
              to="/chat"
              className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition duration-200"
            >
              Chat
            </Link>
            <span className="text-gray-600 text-sm">
              Welcome, {user?.email}
            </span>
            <button
              onClick={logout}
              className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 active:bg-gray-200 cursor-pointer"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

function AuthenticatedLayout() {
  return (
    <div className="h-screen flex bg-gray-100">
      {/* Class Selector Sidebar */}
      <div className="flex-shrink-0">
        <ClassSelector />
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navigation />

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/chat" element={<Chat />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function UnauthenticatedLayout() {
  return (
    <div className="h-screen bg-gray-100">
      <Routes>
        <Route path="/login" element={<Login key="login" />} />
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Login key="login" />} />
      </Routes>
    </div>
  );
}

function AppContent() {
  const { user, isLoading } = useUserContext();

  // Don't show loading screen - it causes remounts
  // Just render the appropriate layout and let components handle their own loading states
  return (
    <>
      {user ? (
        <ProtectedRoute>
          <AuthenticatedLayout />
        </ProtectedRoute>
      ) : (
        <UnauthenticatedLayout />
      )}
    </>
  );
}

function App() {
  return (
    <Router>
      <UserProvider>
        <ClassProvider>
          <DocumentRefreshProvider>
            <AppContent />
          </DocumentRefreshProvider>
        </ClassProvider>
      </UserProvider>
    </Router>
  );
}

export default App;

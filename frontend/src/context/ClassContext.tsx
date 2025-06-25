import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { useUserContext } from './UserContext';

export interface Class {
  id: string; // UUID from backend
  name: string;
  // Optionally add createdAt if backend provides it
}

interface ClassContextType {
  classes: Class[];
  selectedClass: Class | null;
  addClass: (name: string) => Promise<void>;
  selectClass: (classId: string) => void;
  deleteClass: (classId: string) => Promise<void>;
  refreshClasses: () => Promise<void>;
}

const ClassContext = createContext<ClassContextType | undefined>(undefined);

export const useClassContext = () => {
  const context = useContext(ClassContext);
  if (context === undefined) {
    throw new Error('useClassContext must be used within a ClassProvider');
  }
  return context;
};

interface ClassProviderProps {
  children: ReactNode;
}

export const ClassProvider: React.FC<ClassProviderProps> = ({ children }) => {
  const [classes, setClasses] = useState<Class[]>([]);
  const [selectedClass, setSelectedClass] = useState<Class | null>(null);
  const { token } = useUserContext();

  // Fetch classes from backend
  const refreshClasses = async () => {
    try {
      const res = await fetch('/api/classes', {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setClasses(data);
      // Auto-select first class if none selected
      if (!selectedClass && data.length > 0) {
        setSelectedClass(data[0]);
      }
    } catch (err) {
      // Optionally handle error
    }
  };

  useEffect(() => {
    if (token) {
      refreshClasses();
    } else {
      setClasses([]);
      setSelectedClass(null);
    }
    // eslint-disable-next-line
  }, [token]);

  const addClass = async (name: string) => {
    const formData = new FormData();
    formData.append('name', name);
    const res = await fetch('/api/classes', {
      method: 'POST',
      body: formData,
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    });
    if (res.ok) {
      await refreshClasses();
    }
  };

  const selectClass = (classId: string) => {
    const classToSelect = classes.find(c => c.id === classId);
    if (classToSelect) {
      setSelectedClass(classToSelect);
    }
  };

  const deleteClass = async (classId: string) => {
    await fetch(`/api/classes/${classId}`, {
      method: 'DELETE',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    });
    await refreshClasses();
    // If we're deleting the selected class, select the first available class
    if (selectedClass?.id === classId) {
      const remainingClasses = classes.filter(c => c.id !== classId);
      setSelectedClass(remainingClasses[0] || null);
    }
  };

  const value: ClassContextType = {
    classes,
    selectedClass,
    addClass,
    selectClass,
    deleteClass,
    refreshClasses,
  };

  return (
    <ClassContext.Provider value={value}>
      {children}
    </ClassContext.Provider>
  );
}; 
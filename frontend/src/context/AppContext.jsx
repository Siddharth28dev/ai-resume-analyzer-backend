// AppContext.jsx
// Paper: "5-stage workflow — state flows through all stages"
// Global state for entire workflow

import { createContext, useContext, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  // Stage tracking — paper: "5 distinct stages"
  const [currentStage, setCurrentStage] = useState(1);

  // Stage 1 — Resume data
  const [resumeData,   setResumeData]   = useState(null);
  const [resumeFile,   setResumeFile]   = useState(null);

  // Stage 2 — Role + JD
  const [selectedRole, setSelectedRole] = useState("");
  const [jdText,       setJdText]       = useState("");
  const [skillGapData, setSkillGapData] = useState(null);

  // Stage 3 — Interview
  const [questions,    setQuestions]    = useState([]);
  const [answers,      setAnswers]      = useState([]);
  const [interviewData, setInterviewData] = useState(null);

  // Stage 4 & 5 — Feedback + Todo
  const [feedbackData, setFeedbackData] = useState(null);
  const [todoList,     setTodoList]     = useState([]);

  const resetAll = () => {
    setCurrentStage(1);
    setResumeData(null);   setResumeFile(null);
    setSelectedRole("");   setJdText("");      setSkillGapData(null);
    setQuestions([]);      setAnswers([]);     setInterviewData(null);
    setFeedbackData(null); setTodoList([]);
  };

  return (
    <AppContext.Provider value={{
      currentStage, setCurrentStage,
      resumeData,   setResumeData,
      resumeFile,   setResumeFile,
      selectedRole, setSelectedRole,
      jdText,       setJdText,
      skillGapData, setSkillGapData,
      questions,    setQuestions,
      answers,      setAnswers,
      interviewData, setInterviewData,
      feedbackData, setFeedbackData,
      todoList,     setTodoList,
      resetAll,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => useContext(AppContext);
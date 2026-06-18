// App.jsx
// Paper: "5-stage workflow guides candidates through career preparation"

import { AppProvider, useApp } from "./context/AppContext";
import ResumeUpload  from "./pages/ResumeUpload";
import RoleSelection from "./pages/RoleSelection";
import Interview     from "./pages/Interview";
import Feedback      from "./pages/Feedback";
import TodoList      from "./pages/TodoList";
import StageBar      from "./components/StageBar";

function WorkflowRouter() {
  const { currentStage } = useApp();
  return (
    <>
      <StageBar />
      {currentStage === 1 && <ResumeUpload />}
      {currentStage === 2 && <RoleSelection />}
      {currentStage === 3 && <Interview />}
      {currentStage === 4 && <Feedback />}
      {currentStage === 5 && <TodoList />}
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <div className="app">
        <WorkflowRouter />
      </div>
    </AppProvider>
  );
}
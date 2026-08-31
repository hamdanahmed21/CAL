function ProblemTracker({ content }) {

  // Find all "Step X" occurrences
  const steps =
    content.match(/Step\s+\d+:/gi) || [];

  const totalSteps = steps.length;

  // If no steps exist, don't show tracker
  if (totalSteps === 0) return null;

  // Assume all detected steps are complete
  const completedSteps = totalSteps;

  const progress =
    Math.round(
      (completedSteps / totalSteps) * 100
    );

  return (
    <div className="cb-problem-tracker">

      <div className="cb-progress-header">
        Problem Progress
      </div>

      <div className="cb-progress-bar">
        <div
          className="cb-progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="cb-progress-text">
        {progress}% Complete
      </div>

      <ul className="cb-step-list">
        {steps.map((step, index) => (
          <li
            key={index}
            className="cb-step-item"
          >
            ✓ {step}
          </li>
        ))}
      </ul>

      {progress === 100 && (
        <div className="cb-completion-badge">
          🏆 Solution Complete
        </div>
      )}

    </div>
  );
}

export default ProblemTracker;
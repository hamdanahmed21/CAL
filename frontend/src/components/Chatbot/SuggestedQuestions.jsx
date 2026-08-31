import React from "react";

/**
 * SuggestedQuestions — displays AI-generated follow-up questions
 *
 * Props:
 *   - suggestions: array of strings (from LLM's [FOLLOW_UPS] block)
 *   - onSelect: function(question) — fires when user clicks a suggestion
 *   - disabled: boolean — disables buttons while loading
 */
const SuggestedQuestions = ({ suggestions = [], onSelect, disabled = false }) => {
  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="cb-suggestions" role="group" aria-label="Suggested next steps">
      <div className="cb-suggestions-divider" aria-hidden="true" />
      <div className="cb-suggestions-header">
        <span className="cb-suggestions-icon" aria-hidden="true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
          </svg>
        </span>
        <span className="cb-suggestions-label">What would you like to explore next?</span>
      </div>
      <div className="cb-suggestions-chips">
        {suggestions.map((question, index) => (
          <button
            key={index}
            className="cb-chip cb-chip--action"
            style={{ animationDelay: `${index * 70 + 120}ms` }}
            onClick={() => onSelect(question)}
            disabled={disabled}
            type="button"
          >
            <span className="cb-chip-icon" aria-hidden="true">↗</span>
            <span className="cb-chip-text">{question}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;

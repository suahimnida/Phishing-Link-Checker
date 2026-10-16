import { useState } from "react";

import { getResponseGuide } from "../../services/api";
import "./AfterClick.css";

// 위험·주의 판정일 때 '이미 눌렀다면?' 안내.
// 상황을 하나 고르면 그 상황의 조치와 꼭 필요한 연락처만 보여 준다 (한꺼번에 다 보여 주지 않는다)
function AfterClick() {
  const [open, setOpen] = useState(false);
  const [guide, setGuide] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && !guide) {
      setError("");
      try {
        setGuide(await getResponseGuide());
      } catch {
        setError("안내를 불러오지 못했어요. 급하면 118(한국인터넷진흥원)에 먼저 전화하세요.");
      }
    }
  }

  const situation = guide?.situations.find((s) => s.id === selected);

  return (
    <div className="after-click">
      <button type="button" className="after-click-toggle" aria-expanded={open} onClick={toggle}>
        이미 눌렀다면?
      </button>

      {open && (
        <div className="after-click-panel">
          {error && <p className="after-click-error">{error}</p>}
          {!guide && !error && <p className="after-click-hint">안내를 불러오는 중이에요.</p>}

          {guide && (
            <>
              <p className="after-click-hint">어디까지 진행했는지 골라 주세요.</p>
              <div className="after-click-options" role="radiogroup" aria-label="진행한 단계">
                {guide.situations.map((s) => (
                  <button
                    type="button"
                    key={s.id}
                    role="radio"
                    aria-checked={selected === s.id}
                    className={selected === s.id ? "selected" : ""}
                    onClick={() => setSelected(s.id)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </>
          )}

          {situation && (
            <div className="after-click-result">
              {situation.actions.map((action) => (
                <div className="after-click-action" key={action.id}>
                  <h4>{action.title}</h4>
                  <ol>
                    {action.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
              ))}

              <div className="after-click-contacts">
                <h4>도움받을 수 있는 곳</h4>
                <ul>
                  {situation.contacts.map((c) => (
                    <li key={c.name}>
                      {c.phone ? (
                        <a className="contact-call" href={`tel:${c.phone}`}>
                          {c.phone}
                        </a>
                      ) : (
                        <a className="contact-call" href={c.url} target="_blank" rel="noopener noreferrer">
                          누리집
                        </a>
                      )}
                      <div>
                        <strong>{c.name}</strong>
                        <p>{c.purpose}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AfterClick;

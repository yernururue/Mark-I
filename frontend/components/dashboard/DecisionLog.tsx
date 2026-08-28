import { Bell, BellOff } from "lucide-react";
import type { Decision } from "@/types/models";

interface DecisionLogProps {
  decisions: Decision[];
}

export default function DecisionLog({ decisions }: DecisionLogProps) {
  if (decisions.length === 0) {
    return (
      <div className="panel-empty">
        <h2>Decision log</h2>
        <div>
          <p>No notification decisions yet.</p>
          <span>Mark-I will show both notifications and deliberate silence here.</span>
        </div>
      </div>
    );
  }

  return (
    <section className="decision-panel">
      <div className="panel-heading">
        <div>
          <h2>Decision log</h2>
          <p>Why Mark-I notified you—or chose not to.</p>
        </div>
      </div>
      
      <div className="decision-list">
        {decisions.map((dec) => {
          const notified = dec.action === "notify";
          
          return (
            <article
              key={dec.id} 
              className="decision-item"
              data-action={notified ? "notify" : "silent"}
            >
              <div className="decision-item__icon" aria-hidden="true">
                {notified ? <Bell size={17} /> : <BellOff size={17} />}
              </div>
              <div className="decision-item__body">
                <div className="decision-item__meta">
                  <span>{notified ? "Notified" : "Stayed silent"}</span>
                  <time dateTime={dec.createdAt}>
                    {new Date(dec.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </time>
                </div>
                <h3>{dec.trigger}</h3>
                <p>{dec.reason}</p>
                <dl>
                  <div><dt>Score</dt><dd>{dec.significanceScore}</dd></div>
                  <div><dt>Threshold</dt><dd>{dec.threshold}</dd></div>
                </dl>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

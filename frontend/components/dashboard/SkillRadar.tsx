import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

interface SkillRadarProps {
  skills?: Record<string, number>;
}

export default function SkillRadar({ skills }: SkillRadarProps) {
  // Convert skills record to recharts data format
  const data = skills 
    ? Object.entries(skills).map(([subject, A]) => ({
        subject,
        A,
        fullMark: 10,
      }))
    : [];

  if (data.length === 0) {
    return (
      <div className="panel-empty">
        <h2>Skill profile</h2>
        <div>
          <p>No skills have been measured yet.</p>
          <span>Connect GitHub and Mark-I will build this profile from observed work.</span>
        </div>
      </div>
    );
  }

  return (
    <section className="skill-panel">
      <div className="panel-heading"><h2>Skill profile</h2></div>
      <div className="skill-chart">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
            <PolarGrid stroke="rgba(255,255,255,0.1)" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
            <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} />
            <Radar
              name="Proficiency"
              dataKey="A"
              stroke="#f05638"
              fill="#f05638"
              fillOpacity={0.4}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#050505', borderColor: 'rgba(255,255,255,0.1)' }}
              itemStyle={{ color: '#f05638' }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

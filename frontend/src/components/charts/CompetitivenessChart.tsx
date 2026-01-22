import { Card } from 'antd';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { Race } from '../../types';

interface CompetitivenessChartProps {
  races: Race[];
}

export const CompetitivenessChart = ({ races }: CompetitivenessChartProps) => {
  const data = Object.entries(
    races.reduce((acc, race) => {
      acc[race.competitiveness_band] = (acc[race.competitiveness_band] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  ).map(([name, count]) => ({ name, count }));

  return (
    <Card title="Races by Competitiveness" variant="borderless">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" fill="#1890ff" />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
};

import { Row, Col, Card, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, TrophyOutlined, DashboardOutlined } from '@ant-design/icons';
import CountUp from 'react-countup';
import type { Race } from '../types';

interface StatCardsProps {
  races: Race[];
}

export const StatCards = ({ races }: StatCardsProps) => {
  const total = races.length;
  const flipOpportunities = races.filter(r => r.winner_party === 'R' && r.margin_pct < 10).length;
  const retentionRisks = races.filter(r => r.winner_party === 'D' && r.margin_pct < 10).length;
  const closestMargin = races.length > 0
    ? Math.min(...races.map(r => r.margin_pct))
    : 0;

  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card>
          <div style={{ color: '#1890ff' }}>
            <Statistic
              title="Total Races"
              value={total}
              prefix={<DashboardOutlined />}
              formatter={(value) => <CountUp end={value as number} duration={0.6} />}
            />
          </div>
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <div style={{ color: '#52c41a' }}>
            <Statistic
              title="Flip Opportunities"
              value={flipOpportunities}
              prefix={<ArrowUpOutlined />}
              formatter={(value) => <CountUp end={value as number} duration={0.6} />}
            />
          </div>
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <div style={{ color: '#faad14' }}>
            <Statistic
              title="Retention Risks"
              value={retentionRisks}
              prefix={<ArrowDownOutlined />}
              formatter={(value) => <CountUp end={value as number} duration={0.6} />}
            />
          </div>
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <div style={{ color: '#cf1322' }}>
            <Statistic
              title="Closest Margin"
              value={closestMargin}
              suffix="%"
              prefix={<TrophyOutlined />}
              formatter={(value) => <CountUp end={value as number} decimals={1} duration={0.6} />}
            />
          </div>
        </Card>
      </Col>
    </Row>
  );
};

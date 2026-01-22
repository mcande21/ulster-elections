import { useState, useMemo } from 'react';
import { Table, Tag, Typography, Input, Card, Spin, Descriptions } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import type { Race, RaceFusionMetrics } from '../types';
import { getFusionMetrics } from '../api/client';

const { Text } = Typography;

interface RacesTableProps {
  races: Race[];
}

interface TableParams {
  pagination?: TablePaginationConfig;
  sortField?: string;
  sortOrder?: string;
  filters?: Record<string, FilterValue | null>;
}

export const RacesTable = ({ races }: RacesTableProps) => {
  const [searchText, setSearchText] = useState('');
  const [tableParams, setTableParams] = useState<TableParams>({
    pagination: {
      current: 1,
      pageSize: 10,
    },
  });
  const [fusionData, setFusionData] = useState<Record<number, RaceFusionMetrics>>({});
  const [loadingFusion, setLoadingFusion] = useState<Record<number, boolean>>({});

  // Filter races based on search text across multiple fields
  const filteredRaces = useMemo(() => {
    if (!searchText) return races;
    const search = searchText.toLowerCase();
    return races.filter(race =>
      race.race_title?.toLowerCase().includes(search) ||
      race.winner_name?.toLowerCase().includes(search) ||
      race.runner_up_name?.toLowerCase().includes(search)
    );
  }, [races, searchText]);

  const getBandColor = (band: string): string => {
    switch (band) {
      case 'Thin':
        return 'red';
      case 'Lean':
        return 'orange';
      case 'Likely':
        return 'gold';
      case 'Safe':
        return 'green';
      default:
        return 'default';
    }
  };

  const getPartyColor = (party: string): string => {
    const p = party.toLowerCase();
    if (p.includes('dem')) return 'blue';
    if (p.includes('rep')) return 'red';
    if (p.includes('con')) return 'purple';
    if (p.includes('wor')) return 'orange';
    if (p.includes('ind')) return 'cyan';
    return 'default';
  };

  const getLeverageTag = (leverage: number | null): JSX.Element | null => {
    if (leverage === null) return null;
    if (leverage > 1.5) return <Tag color="red">High Leverage</Tag>;
    if (leverage > 1.0) return <Tag color="orange">Moderate Leverage</Tag>;
    return <Tag color="green">Low Leverage</Tag>;
  };

  const handleExpand = async (expanded: boolean, record: Race) => {
    if (expanded && !fusionData[record.id]) {
      setLoadingFusion(prev => ({ ...prev, [record.id]: true }));
      try {
        const data = await getFusionMetrics(record.id);
        setFusionData(prev => ({ ...prev, [record.id]: data }));
      } catch (error) {
        console.error('Failed to load fusion metrics:', error);
      } finally {
        setLoadingFusion(prev => ({ ...prev, [record.id]: false }));
      }
    }
  };

  const renderFusionDetails = (record: Race) => {
    if (loadingFusion[record.id]) {
      return <Spin />;
    }

    const data = fusionData[record.id];
    if (!data) {
      return <div>No fusion data available</div>;
    }

    return (
      <div style={{ padding: '16px', background: '#fafafa' }}>
        <Descriptions title="Fusion Voting Analysis" bordered column={2}>
          <Descriptions.Item label="Margin of Victory">
            {data.margin_of_victory.toLocaleString()} votes
          </Descriptions.Item>
          {data.decisive_minor_party && (
            <Descriptions.Item label="Decisive Minor Party">
              <Tag color={getPartyColor(data.decisive_minor_party)}>
                {data.decisive_minor_party}
              </Tag>
            </Descriptions.Item>
          )}
        </Descriptions>

        <div style={{ marginTop: 24 }}>
          <Typography.Title level={5}>Winner: {data.winner_metrics.candidate_name}</Typography.Title>
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Main Party Votes">
              {data.winner_metrics.main_party_votes.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="Minor Party Votes">
              {data.winner_metrics.minor_party_votes.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="Minor Party Share">
              {data.winner_metrics.minor_party_share.toFixed(1)}%
            </Descriptions.Item>
            <Descriptions.Item label="Leverage">
              {getLeverageTag(data.winner_leverage)}
            </Descriptions.Item>
          </Descriptions>
          <div style={{ marginTop: 12 }}>
            <strong>Party Lines:</strong>
            <div style={{ marginTop: 8 }}>
              {data.winner_metrics.party_lines.map((line, idx) => (
                <Tag key={idx} color={getPartyColor(line.party)} style={{ marginBottom: 4 }}>
                  {line.party}: {line.votes.toLocaleString()} ({line.share_pct.toFixed(1)}%)
                </Tag>
              ))}
            </div>
          </div>
        </div>

        {data.runner_up_metrics && (
          <div style={{ marginTop: 24 }}>
            <Typography.Title level={5}>Runner-up: {data.runner_up_metrics.candidate_name}</Typography.Title>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Main Party Votes">
                {data.runner_up_metrics.main_party_votes.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Minor Party Votes">
                {data.runner_up_metrics.minor_party_votes.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Minor Party Share">
                {data.runner_up_metrics.minor_party_share.toFixed(1)}%
              </Descriptions.Item>
              <Descriptions.Item label="Leverage">
                {getLeverageTag(data.runner_up_leverage)}
              </Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 12 }}>
              <strong>Party Lines:</strong>
              <div style={{ marginTop: 8 }}>
                {data.runner_up_metrics.party_lines.map((line, idx) => (
                  <Tag key={idx} color={getPartyColor(line.party)} style={{ marginBottom: 4 }}>
                    {line.party}: {line.votes.toLocaleString()} ({line.share_pct.toFixed(1)}%)
                  </Tag>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const columns: ColumnsType<Race> = [
    {
      title: 'County',
      dataIndex: 'county',
      key: 'county',
      sorter: (a, b) => a.county.localeCompare(b.county),
      filters: Array.from(new Set(races.map(r => r.county))).map(county => ({
        text: county,
        value: county,
      })),
      onFilter: (value, record) => record.county === value,
    },
    {
      title: 'Race',
      dataIndex: 'race_title',
      key: 'race_title',
      sorter: (a, b) => a.race_title.localeCompare(b.race_title),
    },
    {
      title: 'Winner',
      key: 'winner',
      render: (_, record) => (
        <div>
          <div>{record.winner_name}</div>
          <Text type="secondary" style={{ fontSize: '12px' }}>{record.winner_party}</Text>
        </div>
      ),
    },
    {
      title: 'Runner-up',
      key: 'runner_up',
      render: (_, record) => (
        <div>
          <div>{record.runner_up_name}</div>
          <Text type="secondary" style={{ fontSize: '12px' }}>{record.runner_up_party}</Text>
        </div>
      ),
    },
    {
      title: 'Margin',
      dataIndex: 'margin_pct',
      key: 'margin_pct',
      sorter: (a, b) => a.margin_pct - b.margin_pct,
      render: (margin: number) => `${margin.toFixed(1)}%`,
      defaultSortOrder: 'ascend',
    },
    {
      title: 'Competitiveness',
      dataIndex: 'competitiveness_band',
      key: 'competitiveness_band',
      filters: [
        { text: 'Thin', value: 'Thin' },
        { text: 'Lean', value: 'Lean' },
        { text: 'Likely', value: 'Likely' },
        { text: 'Safe', value: 'Safe' },
      ],
      onFilter: (value, record) => record.competitiveness_band === value,
      render: (band: string) => (
        <Tag color={getBandColor(band)}>{band}</Tag>
      ),
    },
  ];

  const handleTableChange = (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Race> | SorterResult<Race>[]
  ) => {
    setTableParams({
      pagination,
      filters,
      ...sorter,
    });
  };

  return (
    <Card title="Race Details" style={{ marginTop: 24 }}>
      <Input
        placeholder="Search races, winners, runner-ups..."
        prefix={<SearchOutlined />}
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        allowClear
        style={{ marginBottom: 16, maxWidth: 400 }}
      />
      <Table
        columns={columns}
        dataSource={filteredRaces}
        rowKey="id"
        pagination={tableParams.pagination}
        onChange={handleTableChange}
        expandable={{
          expandedRowRender: renderFusionDetails,
          onExpand: handleExpand,
        }}
      />
    </Card>
  );
};

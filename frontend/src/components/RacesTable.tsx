import { useState, useMemo } from 'react';
import { Table, Tag, Typography, Input, Card } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';
import type { Race } from '../types';

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
      />
    </Card>
  );
};

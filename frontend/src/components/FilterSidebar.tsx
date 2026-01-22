import { Card, Checkbox, Button, Space, Typography, Divider } from 'antd';
import { FilterOutlined, ClearOutlined } from '@ant-design/icons';
import type { FilterOptions } from '../types';

const { Title } = Typography;

interface FilterSidebarProps {
  filters: Record<string, string>;
  onFilterChange: (key: string, value: string) => void;
  onClearFilters: () => void;
  filterOptions?: FilterOptions;
}

export const FilterSidebar = ({ filters, onFilterChange, onClearFilters, filterOptions }: FilterSidebarProps) => {
  const counties = filterOptions?.counties || [];
  const raceTypes = filterOptions?.raceTypes || [];

  return (
    <Card
      title={
        <Space>
          <FilterOutlined />
          <Title level={4} style={{ margin: 0 }}>Filters</Title>
        </Space>
      }
      variant="borderless"
    >
      <div style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 8 }}>County</Title>
        <Checkbox.Group
          options={counties.map(c => ({ label: c, value: c }))}
          value={filters.county ? filters.county.split(',') : []}
          onChange={(values) => onFilterChange('county', values.join(','))}
          style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
        />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      <div style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 8 }}>Competitiveness</Title>
        <Checkbox.Group
          options={[
            { label: 'Thin (<5%)', value: 'Thin' },
            { label: 'Lean (5-10%)', value: 'Lean' },
            { label: 'Likely (10-20%)', value: 'Likely' },
            { label: 'Safe (>20%)', value: 'Safe' },
          ]}
          value={filters.competitiveness ? filters.competitiveness.split(',') : []}
          onChange={(values) => onFilterChange('competitiveness', values.join(','))}
          style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
        />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      <div style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 8 }}>Race Type</Title>
        <Checkbox.Group
          options={raceTypes.map(r => ({ label: r, value: r }))}
          value={filters.raceType ? filters.raceType.split(',') : []}
          onChange={(values) => onFilterChange('raceType', values.join(','))}
          style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
        />
      </div>

      <Button
        type="default"
        icon={<ClearOutlined />}
        onClick={onClearFilters}
        block
      >
        Clear Filters
      </Button>
    </Card>
  );
};

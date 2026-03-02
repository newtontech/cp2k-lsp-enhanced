import * as dataIndex from '../src/data/index';
import { KeywordDatabase, KeywordInfo, SectionInfo } from '../src/data/keyword-database';

describe('Data Index', () => {
  it('should export KeywordDatabase', () => {
    expect(dataIndex.KeywordDatabase).toBe(KeywordDatabase);
  });

  it('should be able to create KeywordDatabase instance', () => {
    const db = new dataIndex.KeywordDatabase();
    expect(db).toBeInstanceOf(KeywordDatabase);
    expect(typeof db.getSection).toBe('function');
    expect(typeof db.getKeyword).toBe('function');
  });
});

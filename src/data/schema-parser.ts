/**
 * CP2K XML Schema Parser
 * 
 * Parses CP2K's official XML schema exported by `cp2k --xml` command.
 * Extracts sections, keywords, types, constraints, and allowed values.
 */

import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

export interface SchemaKeyword {
  name: string;
  aliases?: string[];
  description?: string;
  dataType: 'STRING' | 'INTEGER' | 'REAL' | 'LOGICAL' | 'ENUM' | 'STRING_LIST' | 'REAL_LIST' | 'INTEGER_LIST';
  defaultValue?: string;
  allowedValues?: string[];
  units?: string[];
  loneValue?: boolean;
  repeats?: boolean;
  deprecated?: boolean;
  required?: boolean;
  defaultUnit?: string;
  defaultVar?: string;
  nVar?: number;
}

export interface SchemaSection {
  name: string;
  aliases?: string[];
  description?: string;
  keywords: Map<string, SchemaKeyword>;
  subsections: Map<string, SchemaSection>;
  repeats?: boolean;
  required?: boolean;
  deprecated?: boolean;
  parentPath: string[];
}

export interface CP2KSchema {
  version: string;
  sections: Map<string, SchemaSection>;
  keywords: Map<string, SchemaKeyword>;
}

export class SchemaParser {
  private cp2kPath: string;
  private schema: CP2KSchema | null = null;
  private schemaCachePath: string;
  
  constructor(cp2kPath: string = 'cp2k', cacheDir?: string) {
    this.cp2kPath = cp2kPath;
    this.schemaCachePath = cacheDir 
      ? path.join(cacheDir, 'cp2k-schema.json')
      : path.join(process.cwd(), 'data', 'cp2k-schema-cache.json');
  }

  /**
   * Load schema from cache or generate from CP2K
   */
  async loadSchema(forceRefresh: boolean = false): Promise<CP2KSchema> {
    // Return cached schema if available
    if (this.schema) {
      return this.schema;
    }

    // Try to load from cache file
    if (!forceRefresh && fs.existsSync(this.schemaCachePath)) {
      try {
        const cached = JSON.parse(fs.readFileSync(this.schemaCachePath, 'utf-8'));
        this.schema = this.deserializeSchema(cached);
        return this.schema;
      } catch (error) {
        console.warn('Failed to load cached schema:', error);
      }
    }

    // Generate schema from CP2K
    const schema = await this.generateSchemaFromCP2K();
    this.schema = schema;

    // Cache to file
    this.cacheSchema(schema);

    return schema;
  }

  /**
   * Generate schema by running cp2k --xml
   */
  private async generateSchemaFromCP2K(): Promise<CP2KSchema> {
    return new Promise((resolve, reject) => {
      let stdout = '';
      let stderr = '';
      let resolved = false;

      const proc = spawn(this.cp2kPath, ['--xml'], {
        timeout: 60000,
        stdio: ['pipe', 'pipe', 'pipe']
      });

      proc.stdout?.on('data', (data) => {
        stdout += data.toString();
      });

      proc.stderr?.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('error', (err) => {
        if (!resolved) {
          resolved = true;
          reject(new Error(`Failed to spawn CP2K: ${err.message}`));
        }
      });

      proc.on('close', (code) => {
        if (!resolved) {
          resolved = true;
          if (code === 0 && stdout) {
            try {
              const schema = this.parseXMLSchema(stdout);
              resolve(schema);
            } catch (error) {
              reject(new Error(`Failed to parse XML schema: ${error}`));
            }
          } else {
            // Return empty schema if CP2K not available
            resolve(this.getEmptySchema());
          }
        }
      });

      // Timeout
      setTimeout(() => {
        if (!resolved) {
          resolved = true;
          proc.kill();
          resolve(this.getEmptySchema());
        }
      }, 60000);
    });
  }

  /**
   * Parse CP2K XML schema output
   */
  private parseXMLSchema(xmlContent: string): CP2KSchema {
    const schema: CP2KSchema = {
      version: '',
      sections: new Map(),
      keywords: new Map()
    };

    // Simple XML parsing without external dependencies
    // Extract version
    const versionMatch = xmlContent.match(/<CP2K[^>]*version=["']([^"']+)["']/i);
    if (versionMatch) {
      schema.version = versionMatch[1];
    }

    // Parse sections recursively
    this.parseSections(xmlContent, schema, []);

    return schema;
  }

  /**
   * Parse sections from XML content
   */
  private parseSections(
    content: string, 
    schema: CP2KSchema, 
    parentPath: string[]
  ): void {
    // Find all SECTION elements
    const sectionRegex = /<SECTION([^>]*)>([\s\S]*?)<\/SECTION>/gi;
    let match;

    while ((match = sectionRegex.exec(content)) !== null) {
      const attributes = match[1];
      const body = match[2];

      // Parse section attributes
      const name = this.extractAttribute(attributes, 'NAME') || 
                   this.extractAttribute(attributes, 'name');
      if (!name) continue;

      const section: SchemaSection = {
        name: name.toUpperCase(),
        aliases: this.parseList(this.extractAttribute(attributes, 'ALIASES')),
        description: this.extractAttribute(attributes, 'DESCRIPTION') ||
                     this.extractCDATA(body, 'DESCRIPTION'),
        keywords: new Map(),
        subsections: new Map(),
        repeats: this.parseBoolean(this.extractAttribute(attributes, 'REPEATS')),
        required: this.parseBoolean(this.extractAttribute(attributes, 'REQUIRED')),
        deprecated: this.parseBoolean(this.extractAttribute(attributes, 'DEPRECATED')),
        parentPath
      };

      // Parse keywords in this section
      this.parseKeywords(body, section, schema);

      // Parse nested sections
      this.parseNestedSections(body, section, schema);

      schema.sections.set(section.name, section);
    }
  }

  /**
   * Parse keywords from section body
   */
  private parseKeywords(
    content: string, 
    section: SchemaSection, 
    schema: CP2KSchema
  ): void {
    const keywordRegex = /<KEYWORD([^>]*)>([\s\S]*?)<\/KEYWORD>/gi;
    let match;

    while ((match = keywordRegex.exec(content)) !== null) {
      const attributes = match[1];
      const body = match[2];

      const name = this.extractAttribute(attributes, 'NAME') ||
                   this.extractAttribute(attributes, 'name');
      if (!name) continue;

      const keyword: SchemaKeyword = {
        name: name.toUpperCase(),
        aliases: this.parseList(this.extractAttribute(attributes, 'ALIASES')),
        description: this.extractAttribute(attributes, 'DESCRIPTION') ||
                     this.extractCDATA(body, 'DESCRIPTION'),
        dataType: this.parseDataType(
          this.extractAttribute(attributes, 'DATA_TYPE') ||
          this.extractAttribute(attributes, 'TYPE') || 'STRING'
        ),
        defaultValue: this.extractAttribute(attributes, 'DEFAULT_VALUE') ||
                      this.extractAttribute(attributes, 'DEFAULT'),
        allowedValues: this.parseList(
          this.extractAttribute(attributes, 'ALLOWED_VALUES') ||
          this.extractCDATA(body, 'ALLOWED_VALUES')
        ),
        units: this.parseList(this.extractAttribute(attributes, 'UNITS')),
        loneValue: this.parseBoolean(this.extractAttribute(attributes, 'LONE_VALUE')),
        repeats: this.parseBoolean(this.extractAttribute(attributes, 'REPEATS')),
        deprecated: this.parseBoolean(this.extractAttribute(attributes, 'DEPRECATED')),
        required: this.parseBoolean(this.extractAttribute(attributes, 'REQUIRED')),
        defaultUnit: this.extractAttribute(attributes, 'DEFAULT_UNIT'),
        defaultVar: this.extractAttribute(attributes, 'DEFAULT_VAR'),
        nVar: this.parseInt(this.extractAttribute(attributes, 'N_VAR'))
      };

      section.keywords.set(keyword.name, keyword);
      schema.keywords.set(keyword.name, keyword);
    }
  }

  /**
   * Parse nested sections
   */
  private parseNestedSections(
    content: string,
    parentSection: SchemaSection,
    schema: CP2KSchema
  ): void {
    const sectionRegex = /<SECTION([^>]*)>([\s\S]*?)<\/SECTION>/gi;
    let match;

    while ((match = sectionRegex.exec(content)) !== null) {
      const attributes = match[1];
      const body = match[2];

      const name = this.extractAttribute(attributes, 'NAME') ||
                   this.extractAttribute(attributes, 'name');
      if (!name) continue;

      const section: SchemaSection = {
        name: name.toUpperCase(),
        aliases: this.parseList(this.extractAttribute(attributes, 'ALIASES')),
        description: this.extractAttribute(attributes, 'DESCRIPTION') ||
                     this.extractCDATA(body, 'DESCRIPTION'),
        keywords: new Map(),
        subsections: new Map(),
        repeats: this.parseBoolean(this.extractAttribute(attributes, 'REPEATS')),
        required: this.parseBoolean(this.extractAttribute(attributes, 'REQUIRED')),
        deprecated: this.parseBoolean(this.extractAttribute(attributes, 'DEPRECATED')),
        parentPath: [...parentSection.parentPath, parentSection.name]
      };

      // Parse keywords
      this.parseKeywords(body, section, schema);

      // Recursively parse deeper nested sections
      this.parseNestedSections(body, section, schema);

      parentSection.subsections.set(section.name, section);
      schema.sections.set(section.name, section);
    }
  }

  /**
   * Extract attribute value from XML element
   */
  private extractAttribute(element: string, name: string): string | undefined {
    const regex = new RegExp(`${name}=["']([^"']*)["']`, 'i');
    const match = element.match(regex);
    return match ? match[1] : undefined;
  }

  /**
   * Extract CDATA content
   */
  private extractCDATA(content: string, tagName: string): string | undefined {
    const regex = new RegExp(`<${tagName}[^>]*><!\\[CDATA\\[([\\s\\S]*?)\\]\\]></${tagName}>`, 'i');
    const match = content.match(regex);
    return match ? match[1].trim() : undefined;
  }

  /**
   * Parse list from comma-separated string
   */
  private parseList(value: string | undefined): string[] | undefined {
    if (!value) return undefined;
    return value.split(',').map(v => v.trim()).filter(v => v);
  }

  /**
   * Parse boolean value
   */
  private parseBoolean(value: string | undefined): boolean | undefined {
    if (!value) return undefined;
    return value.toLowerCase() === 'true' || value === '1' || value.toLowerCase() === 'yes';
  }

  /**
   * Parse integer value
   */
  private parseInt(value: string | undefined): number | undefined {
    if (!value) return undefined;
    const parsed = Number.parseInt(value, 10);
    return isNaN(parsed) ? undefined : parsed;
  }

  /**
   * Parse data type string to enum
   */
  private parseDataType(typeStr: string): SchemaKeyword['dataType'] {
    const upper = typeStr.toUpperCase();
    
    if (upper.includes('STRING_LIST') || upper.includes('WORD')) {
      return 'STRING_LIST';
    }
    if (upper.includes('REAL_LIST') || upper.includes('FLOAT_LIST')) {
      return 'REAL_LIST';
    }
    if (upper.includes('INTEGER_LIST') || upper.includes('INT_LIST')) {
      return 'INTEGER_LIST';
    }
    if (upper.includes('INTEGER') || upper.includes('INT')) {
      return 'INTEGER';
    }
    if (upper.includes('REAL') || upper.includes('FLOAT') || upper.includes('DOUBLE')) {
      return 'REAL';
    }
    if (upper.includes('LOGICAL') || upper.includes('BOOL')) {
      return 'LOGICAL';
    }
    if (upper.includes('ENUM') || upper.includes('ENUMERATION')) {
      return 'ENUM';
    }
    
    return 'STRING';
  }

  /**
   * Get empty schema (fallback when CP2K not available)
   */
  private getEmptySchema(): CP2KSchema {
    return {
      version: '',
      sections: new Map(),
      keywords: new Map()
    };
  }

  /**
   * Cache schema to file
   */
  private cacheSchema(schema: CP2KSchema): void {
    try {
      const cacheDir = path.dirname(this.schemaCachePath);
      if (!fs.existsSync(cacheDir)) {
        fs.mkdirSync(cacheDir, { recursive: true });
      }
      
      const serialized = this.serializeSchema(schema);
      fs.writeFileSync(this.schemaCachePath, JSON.stringify(serialized, null, 2), 'utf-8');
    } catch (error) {
      console.warn('Failed to cache schema:', error);
    }
  }

  /**
   * Serialize schema for JSON storage
   */
  private serializeSchema(schema: CP2KSchema): any {
    return {
      version: schema.version,
      sections: Array.from(schema.sections.entries()).map(([name, section]) => ({
        ...section,
        keywords: Array.from(section.keywords.entries()),
        subsections: Array.from(section.subsections.keys())
      })),
      keywords: Array.from(schema.keywords.entries())
    };
  }

  /**
   * Deserialize schema from JSON
   */
  private deserializeSchema(data: any): CP2KSchema {
    const schema: CP2KSchema = {
      version: data.version || '',
      sections: new Map(),
      keywords: new Map()
    };

    // Restore sections
    if (data.sections) {
      for (const sectionData of data.sections) {
        const section: SchemaSection = {
          name: sectionData.name,
          aliases: sectionData.aliases,
          description: sectionData.description,
          keywords: new Map(sectionData.keywords || []),
          subsections: new Map(),
          repeats: sectionData.repeats,
          required: sectionData.required,
          deprecated: sectionData.deprecated,
          parentPath: sectionData.parentPath || []
        };
        schema.sections.set(section.name, section);
      }
    }

    // Restore keywords
    if (data.keywords) {
      for (const [name, keyword] of data.keywords) {
        schema.keywords.set(name, keyword as SchemaKeyword);
      }
    }

    return schema;
  }

  /**
   * Get section by name
   */
  getSection(name: string): SchemaSection | undefined {
    return this.schema?.sections.get(name.toUpperCase());
  }

  /**
   * Get keyword by name
   */
  getKeyword(name: string): SchemaKeyword | undefined {
    return this.schema?.keywords.get(name.toUpperCase());
  }

  /**
   * Search sections by query
   */
  searchSections(query: string): SchemaSection[] {
    if (!this.schema) return [];
    
    const upperQuery = query.toUpperCase();
    return Array.from(this.schema.sections.values())
      .filter(s => 
        s.name.includes(upperQuery) ||
        s.description?.toUpperCase().includes(upperQuery)
      );
  }

  /**
   * Search keywords by query
   */
  searchKeywords(query: string): SchemaKeyword[] {
    if (!this.schema) return [];
    
    const upperQuery = query.toUpperCase();
    return Array.from(this.schema.keywords.values())
      .filter(k =>
        k.name.includes(upperQuery) ||
        k.description?.toUpperCase().includes(upperQuery) ||
        k.allowedValues?.some(v => v.toUpperCase().includes(upperQuery))
      );
  }
}

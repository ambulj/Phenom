export interface WorkspaceFileChange {
  path: string;
  status: string;
  lines_added: number;
  lines_deleted: number;
  is_staged: boolean;
  is_secret: boolean;
}

export interface DeveloperWorkspaceState {
  name: string;
  root_path: string;
  ide_name: string;
  is_git: boolean;
  branch: string | null;
  is_dirty: boolean;
  lines_added: number;
  lines_deleted: number;
  untracked_count: number;
  modified_files: WorkspaceFileChange[];
  is_private: boolean;
  is_focused: boolean;
  last_updated: number;
}

"""project 子命令实现"""
import sys
from opengrid.project.manager import ProjectManager
from opengrid.cli.utils import parse_dimensions


def add_parser(subparsers):
    parser = subparsers.add_parser('project', help='项目管理')
    sub = parser.add_subparsers(dest='project_command', required=True)

    # list
    sub.add_parser('list', help='列出项目')

    # create
    create_p = sub.add_parser('create', help='创建项目')
    create_p.add_argument('name', help='项目名称')
    create_p.add_argument('dimensions', help='抽屉尺寸，如 265x365 或 265x365:2（份数）')

    # show
    show_p = sub.add_parser('show', help='显示项目')
    show_p.add_argument('name', help='项目名称')

    parser.set_defaults(func=handle_project)
    return parser


def _get_projects_dir():
    """获取项目目录，默认使用配置中的输出目录"""
    from pathlib import Path
    try:
        from opengrid.config import load_config
        config = load_config()
        output_dir = config.get('output', {}).get('stl_dir', '~/3D打印/opengrid/')
        projects_path = Path(output_dir).expanduser()
    except FileNotFoundError:
        # 如果没有配置文件，使用默认目录
        projects_path = Path('~/3D打印/opengrid/').expanduser()

    # 确保目录存在
    projects_path.mkdir(parents=True, exist_ok=True)
    return str(projects_path)


def handle_project(args):
    """处理 project 命令"""
    projects_dir = _get_projects_dir()
    mgr = ProjectManager(projects_dir)
    cmd = args.project_command

    if cmd == 'list':
        projects = mgr.list_projects()
        if not projects:
            print("暂无项目")
            return
        for p in projects:
            print(f"{p.name}")

    elif cmd == 'create':
        # 解析尺寸
        dims = parse_dimensions([args.dimensions])
        if not dims:
            print(f"错误: 无效的尺寸格式 '{args.dimensions}'", file=sys.stderr)
            print("支持的格式: 265x365, 265x365:2, 265 365", file=sys.stderr)
            sys.exit(1)

        width, depth, copies = dims[0]

        # 构建 drawers 列表
        drawers = [{
            "name": args.name,
            "width": width,
            "depth": depth,
            "copies": copies
        }]

        # 创建项目
        project_path = mgr.create_project(args.name, drawers)
        print(f"创建项目: {args.name}")
        print(f"尺寸: {width}x{depth}")
        print(f"路径: {project_path}")

    elif cmd == 'show':
        project_path = mgr.get_project_path(args.name)
        if not project_path:
            print(f"错误: 项目 '{args.name}' 不存在", file=sys.stderr)
            sys.exit(1)

        import yaml
        config_path = project_path / "project.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            print(f"项目: {config.get('name')}")
            print(f"创建时间: {config.get('created')}")
            print(f"状态: {config.get('status')}")
            print(f"抽屉:")
            for drawer in config.get('drawers', []):
                print(f"  - {drawer.get('name')}: {drawer.get('width')}x{drawer.get('depth')} x {drawer.get('copies')}")
        else:
            print(f"项目路径: {project_path}")


__all__ = ['add_parser']

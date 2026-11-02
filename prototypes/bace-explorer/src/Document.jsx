import {useMemo} from 'react';
import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import {sourceSegments} from './graph-model';

const parser=unified().use(remarkParse).use(remarkGfm);

export function Document({text,dcs=[],renderSegment}){
  const tree=useMemo(()=>parser.parse(text),[text]);
  function render(node,key){
    const children=()=>node.children?.map((child,i)=>render(child,`${key}-${i}`));
    switch(node.type){
      case 'root':return children();
      case 'text':{
        const start=node.position.start.offset,end=node.position.end.offset;
        // Escaped Markdown text may differ from its source. Never guess offsets.
        if(!renderSegment||text.slice(start,end)!==node.value)return node.value;
        return sourceSegments(text,start,end,dcs).map(segment=>renderSegment(segment,`${key}-${segment.start}`));
      }
      case 'paragraph':return <p key={key}>{children()}</p>;
      case 'heading':{const Tag=`h${Math.min(node.depth+1,6)}`;return <Tag key={key}>{children()}</Tag>;}
      case 'table':return <div className="source-table-wrap" key={key}><table><thead>{render(node.children[0],`${key}-0`)}</thead><tbody>{node.children.slice(1).map((child,i)=>render(child,`${key}-${i+1}`))}</tbody></table></div>;
      case 'tableRow':return <tr key={key}>{children()}</tr>;
      case 'tableCell':return <td key={key}>{children()}</td>;
      case 'strong':return <strong key={key}>{children()}</strong>;
      case 'emphasis':return <em key={key}>{children()}</em>;
      case 'delete':return <del key={key}>{children()}</del>;
      case 'list':{const Tag=node.ordered?'ol':'ul';return <Tag key={key}>{children()}</Tag>;}
      case 'listItem':return <li key={key}>{children()}</li>;
      case 'blockquote':return <blockquote key={key}>{children()}</blockquote>;
      case 'inlineCode':return <code key={key}>{node.value}</code>;
      case 'code':return <pre key={key}><code>{node.value}</code></pre>;
      case 'break':return <br key={key}/>;
      case 'thematicBreak':return <hr key={key}/>;
      // Render external links and raw HTML as text; the local reader makes no requests.
      default:return node.children?children():node.value??'';
    }
  }
  return render(tree,'document');
}
